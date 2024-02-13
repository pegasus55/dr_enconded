import datetime
import logging
import os
import re
import shutil
import base64
import zipfile
import unicodedata
import string
import datetime as dt

from odoo import models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ExportFile(models.AbstractModel):
    _name = 'hr.dr.export.file'
    _valid_filename_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    _char_limit = 255

    def clean_filename(self, filename, replace=' '):
        """
        Recibe una cadena de texto y valida que pueda ser un nombre de fichero, eliminando los caracteres no válidos.
        :param filename: El nombre del fichero a comprobar
        :param replace: El caracter a reemplazar
        :return:
        """
        whitelist = self._valid_filename_chars
        # Reemplazar espacios
        for r in replace:
            filename = filename.replace(r, '_')

        # Solo mantener caracteres ASCII válidos
        cleaned_filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode()

        # Solo mantener los caracteres permitidos en 'whitelist'
        cleaned_filename = ''.join(c for c in cleaned_filename if c in whitelist)
        if len(cleaned_filename) > self._char_limit:
            _logger.info("Warning, filename truncated because it was over {}. Filenames may no longer be unique".format(
                self._char_limit))
        return cleaned_filename[:self._char_limit]

    def get_temp_folder(self):
        """
        Crea un directorio temporal en este módulo.

        :return: La ruta al directorio donde se guardaran los ficheros temporales.
        """
        current_dir = os.path.dirname(os.path.realpath(__file__))
        parent_dir = os.sep.join(current_dir.split(os.sep)[:-1])
        temp_dir = parent_dir + os.sep + 'temp'

        # Si el directorio no existe lo creo
        if not os.path.isdir(temp_dir):
            try:
                os.makedirs(temp_dir, exist_ok=True)
            except Exception as e:
                _logger.info("ERROR: %s" % e)

        return temp_dir

    def make_temp_file(self, filename, data):
        """
        Crea un fichero en el directorio temporal conteniendo el texto recibido como dato.

        :param filename: Nombre del fichero a crear .
        :param data: Listado de cadenas de texto a adicionar al fichero.
        :return:
        """

        # TODO: manejar posibles errores en la función
        temp_folder = self.get_temp_folder()
        temp_file = temp_folder + os.sep + filename

        with open(temp_file, 'w') as f:
            for item in data:
                f.write(item)

    def zipdir(self, path, zip):
        """
        Recibe un directorio y un fichero comprimido. Empaqueta todos los archivos y carpetas del directorio dentro del
        fichero comprimido (a excepción de él mismo).

        :param path: Cadena con la ruta del directorio.
        :param zip: Fichero ZipFile donde se comprimirá todo
        :return: True/False si fue realizada la operación o no.
        """
        _logger.info("ZIP %s FROM %s" % (zip, path))
        for root, dirs, files in os.walk(path):
            for file in files:
                aux = os.path.join(root, file)
                if aux != zip.filename:
                    zip.write(aux, os.path.relpath(aux, path))
        return True

    def create_zip_file(self, filename):
        """
        Crea un archivo comprimido .ZIP en el directorio temporal con el contenido de este.

        :param filename: El nombre del archivo comprimido (por compatibilidad con sistemas Windows, debe terminar en .zip)
        :return:
        """
        temp_folder = self.get_temp_folder()
        zip_file_path = temp_folder + os.sep + filename

        # Creando el archivo zip
        zip_created = False
        try:
            _logger.info("ZIP FILE NAME: %s" % filename)

            zipf = zipfile.ZipFile(zip_file_path, 'w')
            _logger.info("zip_file_path: %s" % zip_file_path)

            self.zipdir(temp_folder, zipf)
            zipf.close()
            zip_created = True
            _logger.info("ZIP file (%s) was created in %s" % (filename, zip_file_path))
        except Exception as e:
            _logger.error("ZIP creation: %s" % e)
            pass
        return zip_created, zip_file_path

    def pack_redirect(self, att_id=''):
        """
        Recibe el id de un attachment y lo lanza en el navegador.

        :param att_id: Id del Attachment a mostrar
        """

        if att_id:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action = {
                'type': 'ir.actions.act_url',
                'url': base_url + '/web/content/%s' % (att_id),
                'target': 'new'
            }
            return action

    def pack_delete_useless_zip(self, att_id):
        """
        Recibe el id de un Attachment y lo elimina del sistema.

        :param att_id: El id del Attachment a eliminar del sistema.
        """
        if att_id:
            Attachment = self.env['ir.attachment'].sudo()
            att = Attachment.browse(att_id)
            if att:
                att_name = att.name
                try:
                    att.unlink()
                except Exception as e:
                    _logger.error("Delete zip attachment: %s" % e)
                    pass
                try:
                    file_path = self.pack_create_file_path(create=False)
                    os.remove(os.path.join(file_path, att_name))
                except Exception as e:
                    _logger.error("Delete useless ZIP file: %s" % e)
                    pass

    @staticmethod
    def _employee_is_dead(employee, msg):
        if employee.date_of_death:
            if len(employee.beneficiary_id.ids) > 0:
                return True
            else:
                msg.append(_("{} is reported as dead but has no beneficiary defined."))
        return False

    def _format_pichincha_file(self, sequence, employee, value, description, company_account, payment_method,
                               reference=False, company_bic=False):
        """
        Genera la plantilla con los datos para un colaborador con cuenta en el banco de Pichincha.

        :param sequence: Indicador de la secuencia de la línea en el documento.
        :param employee: Objeto hr.employee que representa al colaborador
        :param value: Valor a pagar
        :param description: Brevee descripción de referencia a la línea del documento.
        :param reference: Referencia del documento de pago.
        :param company_bic: Código del banco de la compañía (Solo para pagos en efectivo)
        :return: Cadena de texto con los datos formateados y listado con los mensajes de error generados.
        """
        msg = []  # Aquí se irán almacenando los errores de validación

        # company_account = ""
        # # Validando cuenta empresa
        # company_account = ""
        # if employee.company_id.id:
        #     for journal in self.env['account.journal'].sudo().search(
        #             [('company_id', '=', employee.company_id.id), ('type', '=', 'bank'), ('bank_id.bic', '=', '0010')]):
        #         company_account = journal.bank_acc_number
        #
        #     if company_account == "":
        #         msg.append(_("{} company does not have a bank account defined for Pichincha bank in Accounting module.")
        #                    .format(employee.company_id.name))
        # else:
        #     msg.append(_("{} does not belong to a company.").format(employee.name))

        #payment_method = employee.payment_method

        # Verifica si el colaborador falleció y tiene un beneficiario
        dead_employee = self._employee_is_dead(employee, msg)

        # Validando tipo de cuenta y el número de cuenta
        account_type = ""
        account_number = ""
        if payment_method == "CTA":
            if dead_employee:
                if len(employee.beneficiary_id.bank_ids.ids) > 0:
                    account = employee.beneficiary_id.bank_ids[0]
                    if account.acc_type_id.id:
                        account_type = account.acc_type_id.acc_type
                    else:
                        msg.append(_("{}'s beneficiary has no bank account type defined.").format(employee.name))

                    if account.acc_number:
                        account_number = account.acc_number
                    else:
                        msg.append(_("{}'s beneficiary has no account number defined.").format(employee.name))
                else:
                    msg.append(_("{}'s beneficiary has no bank account defined.").format(employee.name))
            else:
                if employee.bank_account_id:
                    if employee.bank_account_id.acc_type_id.id:
                        account_type = employee.bank_account_id.acc_type_id.acc_type
                    else:
                        msg.append(_("{} has no bank account type defined.").format(employee.name))

                    if employee.bank_account_id.acc_number:
                        account_number = employee.bank_account_id.acc_number
                    else:
                        msg.append(_("{} has no account number defined.").format(employee.name))
                else:
                    msg.append(_("{} has no bank account defined.").format(employee.name))

        # Validando tipo de identificación y número de identificación
        id_type = ""
        id_number = ""
        if dead_employee:
            if employee.beneficiary_id.vat:
                id_type = "C"
                id_number = employee.beneficiary_id.vat
            else:
                msg.append(_("{}'s beneficiary has no Id or defined.").format(employee.name))
        else:
            if employee.identification_id:
                id_type = "C"
                id_number = employee.identification_id
            elif employee.passport_id:
                id_type = "P"
                id_number = employee.passport_id
            else:
                msg.append(_("{} has no Id or passport defined.").format(employee.name))

        address_parts = []
        if dead_employee:
            if employee.beneficiary_id.street:
                address_parts.append(employee.beneficiary_id.street)
            if employee.beneficiary_id.street2:
                address_parts.append(employee.beneficiary_id.street2)
        else:
            if employee.address_home_id.street:
                address_parts.append(employee.address_home_id.street)
            if employee.address_home_id.street2:
                address_parts.append(employee.address_home_id.street2)

        phone_number = ""
        if dead_employee:
            if employee.beneficiary_id.phone:
                phone_number = employee.beneficiary_id.phone
            elif employee.beneficiary_id.mobile:
                phone_number = employee.beneficiary_id.mobile
        else:
            if employee.address_home_id.phone:
                phone_number = employee.address_home_id.phone
            elif employee.address_home_id.mobile:
                phone_number = employee.address_home_id.mobile

        ad_reference = ''
        if dead_employee:
            if employee.beneficiary_id.email and description:
                ad_reference = "|".join([description, employee.beneficiary_id.email])
            else:
                ad_reference = description if description else ''
            if len(ad_reference) > 100:
                ad_reference = ad_reference[:100]
        else:
            if employee.address_home_id.email and description:
                ad_reference = "|".join([description, employee.address_home_id.email])
            else:
                ad_reference = description if description else ''
            if len(ad_reference) > 100:
                ad_reference = ad_reference[:100]

        currency = employee.company_id.currency_id.name

        bic = ""
        account_holder = ""
        city = ""
        if dead_employee:
            if len(employee.beneficiary_id.bank_ids.ids) > 0:
                bic = employee.beneficiary_id.bank_ids[0].bank_id.bic

                if employee.beneficiary_id.bank_ids[0].acc_holder_name:
                    account_holder = employee.beneficiary_id.bank_ids[0].acc_holder_name
                else:
                    account_holder = employee.beneficiary_id.name

            if employee.beneficiary_id.city:
                city = employee.beneficiary_id.city
        else:
            if employee.bank_account_id.bank_id.bic:
                bic = employee.bank_account_id.bank_id.bic

            if employee.bank_account_id.acc_holder_name:
                account_holder = employee.bank_account_id.acc_holder_name
            else:
                account_holder = employee.name

            if employee.address_home_id.city:
                city = employee.address_home_id.city


        return "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format(
            "PA",
            company_account,
            sequence,
            reference if reference else id_number,
            id_number,
            currency,
            int(value * 100).__str__().replace('.','').replace(',','').zfill(13),
            payment_method,
            company_bic if company_bic and payment_method == 'EFE' else bic,
            account_type,
            account_number,
            id_type,
            id_number,
            account_holder,
            ', '.join(address_parts),
            city,
            phone_number,
            "", # Localidad de pago
            "", # Referencia
            ad_reference
        ), msg

    def _format_pichincha_file_rol(self, sequence, employee, value, description, company_account, payment_method,
                               reference=False):
        """
        Genera la plantilla con los datos para un colaborador con cuenta en el banco de Pichincha para el rol de pago.

        :param sequence: Indicador de la secuencia de la línea en el documento.
        :param employee: Objeto hr.employee que representa al colaborador
        :param value: Valor a pagar
        :param description: Brevee descripción de referencia a la línea del documento.
        :param reference: Referencia del documento de pago.
        :return: Cadena de texto con los datos formateados y listado con los mensajes de error generados.
        """
        msg = []  # Aquí se irán almacenando los errores de validación

        # company_account = ""
        # # Validando cuenta empresa
        # company_account = ""
        # if employee.company_id.id:
        #     for journal in self.env['account.journal'].sudo().search(
        #             [('company_id', '=', employee.company_id.id), ('type', '=', 'bank'), ('bank_id.bic', '=', '0010')]):
        #         company_account = journal.bank_acc_number
        #
        #     if company_account == "":
        #         msg.append(_("{} company does not have a bank account defined for Pichincha bank in Accounting module.")
        #                    .format(employee.company_id.name))
        # else:
        #     msg.append(_("{} does not belong to a company.").format(employee.name))

        # Verifica si el colaborador falleció y tiene un beneficiario
        dead_employee = self._employee_is_dead(employee, msg)

        # Validando tipo de cuenta y el número de cuenta
        account_type = ""
        account_number = ""
        if payment_method == "CTA":
            if dead_employee:
                if len(employee.beneficiary_id.bank_ids.ids) > 0:
                    account = employee.beneficiary_id.bank_ids[0]
                    if account.acc_type_id.id:
                        account_type = account.acc_type_id.acc_type
                    else:
                        msg.append(_("{}'s beneficiary has no bank account type defined.").format(employee.name))

                    if account.acc_number:
                        account_number = account.acc_number
                    else:
                        msg.append(_("{}'s beneficiary has no account number defined.").format(employee.name))
                else:
                    msg.append(_("{}'s beneficiary has no bank account defined.").format(employee.name))
            else:
                if employee.bank_account_id:
                    if employee.bank_account_id.acc_type_id.id:
                        account_type = employee.bank_account_id.acc_type_id.acc_type
                    else:
                        msg.append(_("{} has no bank account type defined.").format(employee.name))

                    if employee.bank_account_id.acc_number:
                        account_number = employee.bank_account_id.acc_number
                    else:
                        msg.append(_("{} has no account number defined.").format(employee.name))
                else:
                    msg.append(_("{} has no bank account defined.").format(employee.name))

        if account_type == 'CTE':
            account_type = 'CC'
        elif account_type == 'AHO':
            account_type = 'AH'

        # Validando tipo de identificación y número de identificación
        id_type = ""
        id_number = ""
        if dead_employee:
            if employee.beneficiary_id.vat:
                id_type = "C"
                id_number = employee.beneficiary_id.vat
            else:
                msg.append(_("{}'s beneficiary has no Id or defined.").format(employee.name))
        else:
            if employee.identification_id:
                id_type = "C"
                id_number = employee.identification_id
            elif employee.passport_id:
                id_type = "P"
                id_number = employee.passport_id
            else:
                msg.append(_("{} has no Id or passport defined.").format(employee.name))

        currency = employee.company_id.currency_id.name

        account_holder = ""
        if dead_employee:
            if len(employee.beneficiary_id.bank_ids.ids) > 0:
                if employee.beneficiary_id.bank_ids[0].acc_holder_name:
                    account_holder = employee.beneficiary_id.bank_ids[0].acc_holder_name
                else:
                    account_holder = employee.beneficiary_id.name
        else:
            if employee.bank_account_id.acc_holder_name:
                account_holder = employee.bank_account_id.acc_holder_name
            else:
                account_holder = employee.name

        return "{sequence}{account_holder}{id_type}{id_number}{value}00000000000000{account_type}{currency}{account_number}C{current_date}          U\r\n".format(
            sequence=sequence.__str__().zfill(16),
            account_holder=re.sub(r'[^\x00-\x7F]','?', account_holder.ljust(32)[:32]),  # Remplaza caracteres no ascii por ?
            id_type=id_type,
            id_number=id_number.ljust(14)[:14],
            value=int(value * 100).__str__().replace('.','').replace(',','').zfill(13),
            account_type=account_type[:2],
            currency= '{currency}{currency}'.format(currency=currency),
            account_number=account_number.zfill(10)[:10],
            current_date=dt.datetime.today().strftime('%Y-%m-%d')
        ), msg

    def _format_produbanco_file(self, sequence, employee, value, description, company_account, payment_method,
                                reference=False, company_bic=False):
        """
        Genera la plantilla con los datos para un colaborador con cuenta en el banco de Produbanco.

        :param sequence: Indicador de la secuencia de la línea en el documento.
        :param employee: Objeto hr.employee que representa al colaborador
        :param value: Valor a pagar
        :param description: Breve descripción de referencia a la línea del documento.
        :param reference: Referencia del documento de pago.
        :param company_bic: Código del banco de la compañía (Solo para pagos en efectivo)
        :return: Cadena de texto con los datos formateados y listado con los mensajes de error generados.
        """
        msg = []  # Aquí se irán almacenando los errores de validación

        # # Validando cuenta empresa
        # company_account=""
        # if employee.company_id.id:
        #     for journal in self.env['account.journal'].sudo().search(
        #             [('company_id', '=', employee.company_id.id), ('type', '=', 'bank'), ('bank_id.bic', '=', '0036')]):
        #         company_account = journal.bank_acc_number
        #
        #     if company_account == "":
        #         msg.append(_("{} company does not have a bank account defined for Produbanco bank in Accounting module.")
        #                    .format(employee.company_id.name))
        # else:
        #     msg.append(_("{} does not belong to a company.").format(employee.name))

        #payment_method = employee.payment_method

        # Verifica si el colaborador falleció y tiene un beneficiario
        dead_employee = self._employee_is_dead(employee, msg)

        # Validando tipo de cuenta y el número de cuenta
        account_type = ""
        account_number = ""
        if payment_method == "CTA":
            if dead_employee:
                if len(employee.beneficiary_id.bank_ids.ids) > 0:
                    account = employee.beneficiary_id.bank_ids[0]
                    if account.acc_type_id.id:
                        account_type = account.acc_type_id.acc_type
                    else:
                        msg.append(_("{}'s beneficiary has no bank account type defined.").format(employee.name))

                    if account.acc_number:
                        account_number = account.acc_number
                    else:
                        msg.append(_("{}'s beneficiary has no account number defined.").format(employee.name))
                else:
                    msg.append(_("{}'s beneficiary has no bank account defined.").format(employee.name))
            else:
                if employee.bank_account_id:
                    if employee.bank_account_id.acc_type_id.id:
                        account_type = employee.bank_account_id.acc_type_id.acc_type
                    else:
                        msg.append(_("{} has no bank account type defined.").format(employee.name))

                    if employee.bank_account_id.acc_number:
                        account_number = employee.bank_account_id.acc_number
                    else:
                        msg.append(_("{} has no account number defined.").format(employee.name))
                else:
                    msg.append(_("{} has no bank account defined.").format(employee.name))

        # Validando tipo de identificación y número de identificación
        id_type = ""
        id_number = ""
        if dead_employee:
            if employee.beneficiary_id.vat:
                id_type = "C"
                id_number = employee.beneficiary_id.vat
            else:
                msg.append(_("{}'s beneficiary has no Id or defined.").format(employee.name))
        else:
            if employee.identification_id:
                id_type = "C"
                id_number = employee.identification_id
            elif employee.passport_id:
                id_type = "P"
                id_number = employee.passport_id
            else:
                msg.append(_("{} has no Id or passport defined.").format(employee.name))

        address_parts = []
        if dead_employee:
            if employee.beneficiary_id.street:
                address_parts.append(employee.beneficiary_id.street)
            if employee.beneficiary_id.street2:
                address_parts.append(employee.beneficiary_id.street2)
        else:
            if employee.address_home_id.street:
                address_parts.append(employee.address_home_id.street)
            if employee.address_home_id.street2:
                address_parts.append(employee.address_home_id.street2)

        phone_number = ""
        if dead_employee:
            if employee.beneficiary_id.phone:
                phone_number = employee.beneficiary_id.phone
            elif employee.beneficiary_id.mobile:
                phone_number = employee.beneficiary_id.mobile
        else:
            if employee.address_home_id.phone:
                phone_number = employee.address_home_id.phone
            elif employee.address_home_id.mobile:
                phone_number = employee.address_home_id.mobile

        descrip = description if description else ''
        if len(descrip) > 100:
            descrip = descrip[:100]

        ad_reference = ''
        if dead_employee:
            ad_reference = employee.beneficiary_id.email if employee.beneficiary_id.email else ''
        else:
            ad_reference = employee.address_home_id.email if employee.address_home_id.email else ''
        if len(ad_reference) > 100:
            ad_reference = ad_reference[:100]

        currency = employee.company_id.currency_id.name

        bic = ""
        account_holder = ""
        city = ""
        if dead_employee:
            if len(employee.beneficiary_id.bank_ids.ids) > 0:
                bic = employee.beneficiary_id.bank_ids[0].bank_id.bic

                if employee.beneficiary_id.bank_ids[0].acc_holder_name:
                    account_holder = employee.beneficiary_id.bank_ids[0].acc_holder_name
                else:
                    account_holder = employee.beneficiary_id.name

            if employee.beneficiary_id.city:
                city = employee.beneficiary_id.city
        else:
            if employee.bank_account_id.bank_id.bic:
                bic = employee.bank_account_id.bank_id.bic

            if employee.bank_account_id.acc_holder_name:
                account_holder = employee.bank_account_id.acc_holder_name
            else:
                account_holder = employee.name

            if employee.address_home_id.city:
                city = employee.address_home_id.city


        #  1- Tipo operación
        #  2- Número cuenta empresa
        #  3- Secuencia
        #  4- (Comprobante de pago)
        #  5- Contrapartida código de beneficiario
        #  6- Moneda
        #  7- Valor a pagar
        #  8- Forma de pago
        #  9- Código banco
        # 10- Tipo de cuenta
        # 11- Número de cuenta
        # 12- Tipo de documento de beneficiario
        # 13- Número de cédula de beneficiario
        # 14- Nombre de beneficiario
        # 15- (Dirección beneficiario)
        # 16- (Ciudad beneficiario)
        # 17- (Teléfono beneficiario)
        # 18- (Localidad de cobro)
        # 19- Referencia
        # 20- (Referencia adicional)
        return "{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}\t{7}\t{8}\t{9}\t{10}\t{11}\t{12}\t{13}\t{14}\t{15}\t{16}\t{17}\t{18}\t{19}\r\n".format(
            "PA",
            company_account,
            sequence,
            reference if reference else '',
            id_number,
            currency,
            int(value * 100).__str__().replace('.','').replace(',',''),
            payment_method,
            company_bic if company_bic and payment_method == 'EFE' else bic,
            account_type,
            account_number,
            id_type,
            id_number,
            account_holder,
            ', '.join(address_parts) or '',
            city or '',
            phone_number or '',
            '', # Localidad de pago
            descrip,
            ad_reference,
        ), msg

    def _get_first_line(self, company, lines, value):
        return 'BPR{nif} {name}{lines}{value}\r\n'.format(
            nif=company.vat.ljust(13)[:13] if company and company.vat else ''.ljust(13),
            name=company.transfer_name if company and company.transfer_name else '',
            lines=lines.__str__().zfill(6),
            value=value.__str__().replace('.','').replace(',','').zfill(15)
        )

    def _get_bank_accounts(self):
        """
        Busca en 'ir.config_parameter' y extrae las cuentas bancarias configuradas para pagos.
        :return: Un diccionario con los BIC de las cuentas como claves su objeto 'res.bank.account' como valor
                 correspondiente a la cuenta por cada banco. Además registra en la clave 'Cash' la cuenta definida para
                 pagos en efectivo.
        """

        accounts = {'Cash': None, 'Main': None}

        config_parameter = self.env['ir.config_parameter'].sudo()

        if config_parameter.get_param('payroll.main.bank.account.id'):
            if config_parameter.get_param('payroll.main.bank.account.id') != '':
                company_account_id = int(config_parameter.get_param('payroll.main.bank.account.id'))
                company_bank_account = self.env['res.partner.bank'].sudo().search([('id', '=', company_account_id)],
                                                                                  limit=1)
                if (len(company_bank_account) > 0):
                    accounts['Main'] = company_bank_account[0]

        if config_parameter.get_param('payroll.cash.bank.account.id'):
            if config_parameter.get_param('payroll.cash.bank.account.id') != '':
                company_account_id = int(config_parameter.get_param('payroll.cash.bank.account.id'))
                company_bank_account = self.env['res.partner.bank'].sudo().search([('id', '=', company_account_id)],
                                                                                  limit=1)
                if (len(company_bank_account) > 0):
                    accounts['Cash'] = company_bank_account[0]

        if config_parameter.get_param('payroll.bank.account.ids'):
            if config_parameter.get_param('payroll.bank.account.ids') != '':
                for id in config_parameter.get_param('payroll.bank.account.ids').split(','):
                    bank_account_id = int (id)
                    bank_account = self.env['res.partner.bank'].sudo().search([('id', '=', bank_account_id)], limit=1)
                    if (len(bank_account) > 0):
                        if bank_account[0].bank_id.bic:
                            accounts[bank_account[0].bank_id.bic] = bank_account[0]

        return accounts

    def _create_text_files(self, payment_lines, description, use_main_account=False):
        """
        Por cada banco se genera un fichero con los documentos de pago y los almacena en un directorio temporal.
        """
        messages = []

        accounts = self._get_bank_accounts()

        if use_main_account:
            if accounts['Main'] is None:
                raise ValidationError(_('You must update "Payments main account" in Settings > Payroll'))

        banks = {'Cash':[]}
        # Agrupando los colaborador por banco.
        for line in payment_lines:
            # Validando forma de pago
            if not line.employee_id.payment_method:
                messages.append(_("{} has no payment method defined.").format(line.employee_id.name))
            elif line.employee_id.payment_method == 'CTA':
                dead_employee = self._employee_is_dead(line.employee_id, messages)
                bic = False
                if dead_employee and len(line.employee_id.beneficiary_id.bank_ids.ids) > 0:
                    bic = line.employee_id.beneficiary_id.bank_ids[0].bank_id.bic
                else:
                    bic = line.employee_id.bank_account_id.bank_id.bic
                if not bic or bic is None:
                    messages.append(_("{} has no bank account defined.").format(line.employee_id.name))
                elif bic in banks.keys():
                    banks[bic].append(line)
                else:
                    banks[bic] = [line]
            else:
                banks['Cash'].append(line)

        for bic, lines in banks.items():
            if bic in accounts.keys():
                if bic == '0010':
                    account = accounts['Main'].acc_number if use_main_account else accounts[bic].acc_number
                    items = []
                    items_rol_pago = []
                    total_value = 0

                    company = False
                    if len(lines) > 0:
                        company = lines[0].employee_id.company_id

                    for idx, line in enumerate(lines):
                        file_line, new_msgs = self._format_pichincha_file(idx + 1, line.employee_id, line.value,
                                                   description, account, 'CTA',
                                                   reference=line.reference if hasattr(line, 'reference') else False)
                        messages.extend(new_msgs)
                        items.append(file_line)

                        file_line, new_msgs = self._format_pichincha_file_rol(idx + 1, line.employee_id, line.value,
                                                  description, account, 'CTA',
                                                  reference=line.reference if hasattr(line, 'reference') else False)
                        messages.extend(new_msgs)
                        items_rol_pago.append(file_line)
                        total_value += int(line.value * 100)
                    items_rol_pago.insert(0, self._get_first_line(company, len(items_rol_pago), total_value))
                    self.make_temp_file(bic + '_Pago_a_proveedores.txt', items)
                    self.make_temp_file(bic + '_Rol_de_pago.txt', items_rol_pago)
                elif bic == '0036':
                    account = accounts['Main'].acc_number if use_main_account else accounts[bic].acc_number
                    items = []
                    for idx, line in enumerate(lines):
                        file_line, new_msgs = self._format_produbanco_file(idx + 1, line.employee_id, line.value,
                                                   description, account, 'CTA',
                                                   reference=line.reference if hasattr(line, 'reference') else False)
                        messages.extend(new_msgs)
                        items.append(file_line)
                    self.make_temp_file(bic + '.txt', items)
                elif bic == 'Cash':
                    if lines is not None and len(lines) > 0:
                        account = accounts['Main'].acc_number if use_main_account else accounts['Cash'].acc_number
                        if accounts['Cash'] is not None:
                            cash_bic = accounts['Cash'].bank_id.bic
                            items = []
                            if cash_bic == '0010':
                                for idx, line in enumerate(lines):
                                    file_line, new_msgs = self._format_pichincha_file(idx + 1, line.employee_id,
                                                  line.value, description, account, 'EFE',
                                                  reference=line.reference if hasattr(line, 'reference') else False,
                                                  company_bic=cash_bic)
                                    messages.extend(new_msgs)
                                    items.append(file_line)
                            elif cash_bic == '0036':
                                for idx, line in enumerate(lines):
                                    file_line, new_msgs = self._format_produbanco_file(idx + 1, line.employee_id,
                                                  line.value, description, account, 'EFE',
                                                  reference=line.reference if hasattr(line, 'reference') else False,
                                                  company_bic=cash_bic)
                                    messages.extend(new_msgs)
                                    items.append(file_line)
                            self.make_temp_file(bic + '_Servipagos.txt', items)
                        else:
                            raise ValidationError(_('You must update your "Cash payments account" in Settings > Payroll'))
            else:
                raise ValidationError(_('You must add a bank account for bank {} in "Banc Accounts" in Settings > '
                                            'Payroll').format(bic))
        return messages

    def _compress_and_show(self, zip_name):
        """
        Comprime y muestra en pantalla el fichero comprimido creado.

        :param zip_name: Nombre del comrpimido (Por compatibilidad con Windows debe terminar en .zip)
        """

        msg = []

        temp_folder_dir = self.get_temp_folder()
        zip_created, zip_file_path = self.create_zip_file(zip_name)
        Attachment = self.env['ir.attachment']

        if zip_created:
            # Create an attachment for the zipped file
            try:
                af = open(zip_file_path, 'rb')
                datas = base64.encodebytes(af.read())
                af.close()
                att = Attachment.sudo().create({
                    'name': zip_name,
                    'type': 'binary',
                    'datas': datas,
                    'datas_fname': zip_name,
                    'mimetype': 'application/zip',
                    'store_fname': zip_name,

                })

                # Create a task to delete the zip file (1 hour after this)
                cron_name = 'Delete useless zip file (%s)' % att.id
                model_id = self.env['ir.model'].sudo().search([
                    ('model', '=', self._name)
                ])
                self.env['ir.cron'].sudo().create({
                    'name': cron_name,
                    'model_id': model_id.id,
                    'state': 'code',
                    'code': 'model.pack_delete_useless_zip(%s)' % att.id,
                    'interval_number': 3,
                    'interval_type': 'minutes',
                    'nextcall': datetime.datetime.now() \
                                + datetime.timedelta(minutes=30),
                    'numbercall': 1,
                    'doall': True
                })
            except Exception as e:
                _logger.error("ZIP attachment: %s" % e)
                msg.append(_("ZIP attachment: %s") % e)
                pass

        # Delete the source files
        try:
            shutil.rmtree(temp_folder_dir)
        except Exception as e:
            _logger.info("Source files deletion: %s" % e)
            _logger.info(temp_folder_dir)
            msg.append(_("Source files deletion: %s") % e)
            pass

        if zip_created:
            return self.pack_redirect(att.id)
        else:
            _logger.error(_('A ZIP file was not created:\n%s') % '\n'.join(msg))
            raise ValidationError(_('A ZIP file was not created:\n%s') % '\n'.join(msg))
