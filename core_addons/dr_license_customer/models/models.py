# -*- coding: utf-8 -*-

import datetime as dt
import json
import os
from pathlib import Path
import platform
import uuid
import sys
import ssl
import xmlrpc.client
from cryptography.fernet import Fernet

from odoo import models, api, _
from odoo.exceptions import ValidationError
from odoo.http import request


class Licenses(object):
    operating_system = ''
    system = ''
    machine = ''
    version = ''
    platform = ''
    mac = ''
    sn = ''
    all_modules = []
    databases = {}
    instances = {}

    KEY = b'd7e9tNARn9GnQ5EG2r3NVzrkxH6PTANh8XYyuKy6JXE='
    MODULE_FOLDER = Path(os.path.realpath(__file__)).parent.parent
    FILE_LOCATIONS = os.path.join(MODULE_FOLDER, 'locations.nkl')
    paths = {'TRIAL': {'APPS_FILE': False, 'DEV_FILE': False, 'LIC_FILE': False, 'EXE_FILE': False, 'DAT_FILE': False}}

    database_name = False
    license_id = False

    def __init__(self, license_id=False):
        self.database_name = request.session.db
        self.license_id = license_id
        self.load_locations()
        self.load_files()

    def get_path(self, license_id=False, path=False):
        if not license_id:
            license_id = 'TRIAL'
        if not path:
            return self.paths.get(license_id, {})
        else:
            return self.paths.get(license_id, {}).get(path, False)

    def get_dates(self):
        """
        Lee de los archivos de comprobación de licencia las fechas de ejecución.
        :return: Listado de cadenas de texto representando cada fecha de ejecución.
        """
        json_str = self.decrypt(self.get_path(self.license_id, 'DAT_FILE'))
        license_dic = json.loads(json_str)
        if license_dic is not None:
            return license_dic.get('dates', [])
        else:
            raise ValidationError(_('You have no license installed or there is a problem with your license files.'))

    def get_executions(self):
        """
        Lee de los archivos de comprobación de licencia la cantidad de ejecuciones.
        :return: Número de ejecuciones realizadas.
        """
        json_str = self.decrypt(self.get_path(self.license_id, 'EXE_FILE'))
        license_dic = json.loads(json_str)
        if license_dic is not None:
            return license_dic.get('executions', 0)
        else:
            raise ValidationError(_('You have no license installed or there is a problem with your license files.'))

    def get_license_id(self, dbname=False):
        """Busca el identificador de la licencia en el listado de bases de datos y lo devuelve."""
        if not dbname:
            dbname = self.database_name
        return self.databases.get(dbname, False)

    def trial_license(self):
        """
        Crea una nueva licencia de prueba para un uso y genera los correspondientes ficheros.
        """
        self.paths = {
            'TRIAL': {
                'APPS_FILE': os.path.join(self.MODULE_FOLDER, 'apps.nkl'),
                'DEV_FILE': os.path.join(self.MODULE_FOLDER, 'devices.nkl'),
                'LIC_FILE': os.path.join(self.MODULE_FOLDER, 'license.nkl'),
                'EXE_FILE': os.path.join(self.MODULE_FOLDER, 'executions.nkl'),
                'DAT_FILE': os.path.join(self.MODULE_FOLDER, 'dates.nkl')
            }
        }
        self._get_server_info()
        self.databases = {self.database_name: 'TRIAL'}
        self.instances = {
            'TRIAL': {
                'expiration_date': dt.datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
                'active_collaborators': 0,
                'devices': [],
                'modules': []
            }
        }

        self.save_files()
        self.set_counters(1, [dt.datetime.today().strftime('%Y-%m-%d %H:%M:%S')])

    def _get_server_info(self):
        """ Obtiene información específica del servidor donde está instalado el sistema. """

        self.operating_system = platform.platform()
        self.system = platform.system()
        self.machine = platform.machine()
        self.version = platform.version()
        self.platform = platform.platform()
        self.mac = self.get_mac_addr()
        self.sn = self.get_machine_sn()

    def get_mac_addr(self):
        mac = hex(uuid.getnode())
        if mac[:2] == '0x':
            mac = mac[2:]
        return mac

    def get_machine_sn(self):
        os_type = sys.platform.lower()
        command = ""
        if "win" in os_type:
            command = "wmic bios get serialnumber"
        elif "linux" in os_type:
            command = "hal-get-property --udi /org/freedesktop/Hal/devices/computer --key system.hardware.uuid"
        elif "darwin" in os_type:
            command = "ioreg -l | grep IOPlatformSerialNumber"
        return os.popen(command).read().replace("\n", "").replace("	", "").replace(" ", "")

    def load_locations(self):
        """
        Almacena los valores de las rutas de los archivos de licencia en un fichero.
        :return: None
        """
        json_str = self.decrypt(self.FILE_LOCATIONS)

        # Creando la estructura si no existe un fichero
        if not json_str:
            self.trial_license()
            self.license_id = 'TRIAL'
        else:
            locations_dict = json.loads(json_str)
            self.databases = locations_dict.get('databases', {})
            self.paths = locations_dict.get('locations', {})

    def increment_counters(self):
        """
        Adiciona la fecha actual al listado de fechas e incrementa el contador de ejecuciones en uno. Actualiza los
        ficheros correspondientes.
        :return: None
        """
        executions = self.get_executions()
        dates = self.get_dates()
        dates.append(dt.datetime.today().strftime('%Y-%m-%d %H:%M:%S'))
        executions += 1
        self.set_counters(executions, dates)

    def set_counters(self, executions, dates):
        """
        Almacena en los ficheros de ejecuciones y contadores los valores recibidos.
        :param executions: Cantidad de ejecuciones
        :param dates: Listado de fechas de ejecución
        :return: None
        """
        json_string = json.dumps({'executions': executions})
        self.encrypt(self.get_path(self.license_id, 'EXE_FILE'), json_string)
        json_string = json.dumps({'dates': dates})
        self.encrypt(self.get_path(self.license_id, 'DAT_FILE'), json_string)

    def save_loc_file(self):
        file_data = {
            'databases': self.databases, 'locations': self.paths
        }
        json_string = json.dumps(file_data)
        self.encrypt(self.FILE_LOCATIONS, json_string)

    def save_lic_file(self):

        # Extrayendo los listados de módulos y dispositivos pues se almacenan por separado.
        instances = {}
        for license_id, instance in self.instances.items():
            ins = instance.copy()

            # Aplicaciones y dispositivos se almacenan en ficheros diferentes a este, no los incluyo aquí.
            ins.pop('devices')
            ins.pop('modules')

            # Los objetos Datetime no son serializables por JSON así que lo convierto a texto plano.
            expiration_date = ins.get('expiration_date')
            if isinstance(expiration_date, dt.datetime):
                ins['expiration_date'] = expiration_date.strftime('%Y-%m-%d %H:%M:%S')
            else:
                ins['expiration_date'] = expiration_date

            instances[license_id] = ins

        file_data = {
            'instances': instances,
            'os': self.operating_system,
            'system': self.system,
            'machine': self.machine,
            'version': self.version,
            'platform': self.platform,
            'mac': self.mac,
            'sn': self.sn
        }
        json_string = json.dumps(file_data)
        self.encrypt(self.get_path(self.license_id, 'LIC_FILE'), json_string)

    def save_dev_file(self):
        file_data = {}
        for license_id, instance in self.instances.items():
            file_data[license_id] = instance.get('devices', [])

        json_string = json.dumps(file_data)
        self.encrypt(self.get_path(self.license_id, 'DEV_FILE'), json_string)

    def save_app_file(self):
        file_data = {'modules': {}, 'all': self.all_modules}
        for license_id, instance in self.instances.items():
            file_data['modules'][license_id] = instance.get('modules', [])

        json_string = json.dumps(file_data)
        self.encrypt(self.get_path(self.license_id, 'APPS_FILE'), json_string)

    def save_files(self):
        self.save_loc_file()
        self.save_lic_file()
        self.save_app_file()
        self.save_dev_file()

    def load_files(self):
        json_str = self.decrypt(self.get_path(self.license_id, 'LIC_FILE'))
        license = json.loads(json_str)
        if license is not None:
            self.operating_system = license.get('os', '')
            self.system = license.get('system', '')
            self.machine = license.get('machine', '')
            self.version = license.get('version', '')
            self.platform = license.get('platform', '')
            self.mac = license.get('mac', '')
            self.sn = license.get('sn', '')
            for lic_id, instance in license.get('instances', {}).items():
                self.instances[lic_id] = self.load_instance(instance)
        else:
            raise ValidationError(_('You have no license installed or there is a problem with your license files.'))

        license = None
        json_str = self.decrypt(self.get_path(self.license_id, 'DEV_FILE'))
        license = json.loads(json_str)
        if license is not None:
            for lic_id, devices in license.items():
                instance = self.instances.get(lic_id, False)
                if instance:
                    instance['devices'] = devices
        else:
            raise ValidationError(_('You have no license installed or there is a problem with your devices file.'))

        license = None
        json_str = self.decrypt(self.get_path(self.license_id, 'APPS_FILE'))
        license = json.loads(json_str)
        if license is not None:
            self.all_modules =  license.get('all', [])
            for lic_id, modules in license.get('modules', {}).items():
                instance = self.instances.get(lic_id, False)
                if instance:
                    instance['modules'] = modules
        else:
            raise ValidationError(_('You have no license installed or there is a problem with your modules file.'))

    def load_instance(self, instance):
        instance_dict = {'expiration_date': False, 'active_collaborators': 0,
                         'devices': [], 'modules': []}
        if instance is not None:
            instance_dict['expiration_date'] = dt.datetime.strptime(
                instance.get('expiration_date', '1970-01-01 00:00:00'), '%Y-%m-%d %H:%M:%S')
            instance_dict['active_collaborators'] = instance.get('active_collaborators', 0)
        return instance_dict

    def set_all_modules(self, all):
        self.all_modules = all

    def add_license(self, license_id, expiration_date, active_collaborators, databases, devices, modules,
                    all_modules, paths, package):
        if license_id in self.instances:
            self.instances.get(license_id).update({
                'expiration_date': expiration_date, 'active_collaborators': active_collaborators,
                'devices': devices, 'modules': modules, 'package': package})
        else:
            self.instances.update({license_id: {
                'expiration_date': expiration_date, 'active_collaborators': active_collaborators,
                'devices': devices, 'modules': modules, 'package': package}})
        for database in databases:
            self.databases.update({database: license_id})

        self.set_all_modules(all_modules)
        self.paths.update({license_id: paths})

    def get_current_instance(self):
        return self.instances.get(self.get_license_id(), False)

    def encrypt(self, file_path, content_string):
        fernet = Fernet(self.KEY)
        with open(file_path, 'wb') as lic_file:
            encrypted_string = fernet.encrypt(bytes(content_string, encoding='utf-8'))
            lic_file.write(encrypted_string)

    def decrypt(self, file_path):
        fernet = Fernet(self.KEY)
        try:
            lic_file = open(file_path, 'rb')
            encrypted_string = lic_file.read()
            return fernet.decrypt(encrypted_string)
        except FileNotFoundError:
            return False


class License(object):
    remote_server_user = 'admin'
    remote_server_password = 'admin'
    remote_server_database = 'hr_v16'
    remote_server_url = 'http://localhost:8069'

    my_licenses = False

    active_collaborators = 0
    package = ""
    expiration_date = dt.datetime.today()
    databases = []
    devices = []
    modules = []
    all_modules = []
    os = ''
    paths = {'APPS_FILE': '', 'DEV_FILE': '', 'LIC_FILE': '', 'EXE_FILE': '', 'DAT_FILE': ''}
    active_db = False
    id_number = False

    def __init__(self, get_param):
        self.my_licenses = Licenses()
        self.remote_server_url = 'https://license.nukleosolutions.com'
        self.remote_server_database = get_param("license.srvr.db", '')
        self.remote_server_user = get_param("license.srvr.user", '')
        self.remote_server_password = 'Stu3puMEEHV%FTGtcr!u'

    def get_expiration_date(self, as_str=False):
        """
        Lee la fecha de vencimiento de los archivos de licencia.
        :param as_str: Si este parámetro tiene valor True el resultado será una cadena de texto.
        :return: Objeto datetime.datetime o str en dependencia de parámetro 'as_str' representando la fecha de
                 vencimiento.
        """
        license = self.my_licenses.get_current_instance()
        if not license:
            raise ValidationError(_('You have no license installed or there is a problem with your license files.'))

        if as_str:
            return license.get('expiration_date').strftime('%Y-%m-%d %H:%M:%S')
        return license.get('expiration_date')

    def get_max_employees(self):
        """
        Lee la cantidad máxima de empleados de los archivos de licencia.
        :return: Número con la cantidad máxima de empleados.
        """
        license = self.my_licenses.get_current_instance()
        if not license:
            raise ValidationError(_('You have no license installed or there is a problem with your license files.'))
        return license.get('active_collaborators', 0)

    def get_nukleo_version(self):
        """
        Lee la cantidad máxima de empleados de los archivos de licencia.
        :return: Número con la cantidad máxima de empleados.
        """
        license = self.my_licenses.get_current_instance()
        if not license:
            raise ValidationError(_('You have no license installed or there is a problem with your license files.'))
        return license.get('package', '')

    def get_databases(self):
        """
        Verifica en los archivos de licencia las bases de datos autorizadas para la licencia.
        :return: listado de nombres de base de datos
        """
        return self.my_licenses.databases.keys()

    def get_apps(self):
        """
        Lee de los archivos de licencia las aplicaciones permitidas.
        :return: Listado de nombres de aplicaciones.
        """
        license = self.my_licenses.get_current_instance()
        if not license:
            raise ValidationError(_('You have no license installed or there is a problem with your license files.'))
        apps = license.get('modules', False)

        return [x['name'] for x in apps]

    def get_apps_tradename(self):
        """
        Lee de los archivos de licencia los nombres comerciales de las aplicaciones permitidas.
        :return: Listado de nombres comerciales de aplicaciones.
        """
        license = self.my_licenses.get_current_instance()
        if not license:
            raise ValidationError(_('You have no license installed or there is a problem with your license files.'))
        apps = license.get('modules', False)

        return [x['tradename'] for x in apps if x['type'] == 'commercial']

    def get_all_apps(self):
        """
        Lee de los archivos de licencia el listado de aplicaciones comercializadas.
        :return: Listado de nombres de aplicaciones.
        """
        return self.my_licenses.all_modules

    def get_devices(self):
        """
        Lee de los archivos de licencia los dispositivos permitidos.
        :return: Listado de números de serie de los dispositivos autorizados.
        """
        license = self.my_licenses.get_current_instance()
        if not license:
            raise ValidationError(_('You have no license installed or there is a problem with your license files.'))
        return license.get('devices', False)

    def request_license(self, id_number):
        """
        Solicita la información de la licencia del servidor de Nukleo usando el web service de Odoo.
        Genera los ficheros de licencia actualizados con la información obtenida.

        :param id_number: Identificador del cliente al solicitar la licencia.
        :return:
        """
        self.id_number = id_number.strip()
        username = self.remote_server_user
        pwd = self.remote_server_password
        dbname = self.remote_server_database
        url = self.remote_server_url

        try:

            gcontext = ssl._create_unverified_context()
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url), context=gcontext)

            uid = common.login(dbname, username, pwd)
            sock = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url), context=gcontext)

            # licenses = sock.execute(dbname, uid, pwd, 'dr.license', 'search', [
            #     ('active', '=', True), ('vat', '=', id_number.strip())])

            licenses = sock.execute_kw(dbname, uid, pwd, 'dr.license', 'search_read',
                                       [[('active', '=', True), ('vat', '=', self.id_number),
                                         ('confirmed', '=', False)]],
                                       {'fields': ['active_collaborators', 'expiration_date',
                                                   'device_ids', 'module_ids', 'os', 'path_ids', 'databases', 'package'
                                                   ], 'limit': 1})

            if len(licenses) > 0:
                lic = licenses[0]

                self.active_collaborators = lic['active_collaborators']
                self.package = lic['package']
                self.expiration_date = dt.datetime.strptime(lic['expiration_date'], '%Y-%m-%d') + dt.timedelta(
                    hours=23, minutes=59, seconds=59, milliseconds=999)
                self.os = lic['os']
                self._extract_databases(lic['databases'])

                paths = sock.execute_kw(dbname, uid, pwd, 'dr.license.file.location', 'search_read',
                                        [[('id', 'in', lic['path_ids'])]], {'fields': ['file', 'path']})
                for file_path in paths:
                    if file_path['path'] != '':
                        self.paths[file_path['file']] = file_path['path']

                devices = sock.execute_kw(dbname, uid, pwd, 'dr.device', 'search_read',
                                           [[('id', 'in', lic['device_ids'])]], {'fields': ['serial_number', 'brand_id', 'model_id']})

                self.devices = []
                for device in devices:
                    self.devices.append({'brand': device['brand_id'][1], 'model': device['model_id'][1], 'sn': device['serial_number']})

                modules = sock.execute_kw(dbname, uid, pwd, 'dr.salable.module', 'search_read',
                                          [[('id', 'in', lic['module_ids'])]], {'fields': ['name', 'tradename', 'type']})

                self.modules = []
                for module in modules:
                    self.modules.append({'name': module['name'], 'tradename': module['tradename'], 'type': module['type']})

                # Obteniendo el listado de todos los módulos comercializados.
                all_modules = sock.execute_kw(dbname, uid, pwd, 'dr.salable.module', 'search_read', [[]],
                                              {'fields': ['name']})

                self.all_modules = []
                for module in all_modules:
                    self.all_modules.append(module['name'])

                self.my_licenses.add_license(license_id=id_number, expiration_date=self.expiration_date,
                                             active_collaborators=self.active_collaborators,
                                             databases=self.databases, devices=self.devices, modules=self.modules,
                                             all_modules=self.all_modules, paths=self.paths, package=self.package)
                self.my_licenses.set_counters(1, [dt.datetime.today().strftime('%Y-%m-%d %H:%M:%S')])
                self.my_licenses.save_files()


                # Confirmo en el server que ya instalé la licencia.
                sock.execute(dbname, uid, pwd, 'dr.license', 'write', lic['id'], {'confirmed': True})

            else:
                raise ValidationError(_('No license update found.'))

            print("Date:{} | Max users: {}\n\tDevices: {}\n\tModules: {}\n\tAll modules: {}\n\tDatabases: {}".format(
                self.expiration_date, self.active_collaborators, self.devices, self.modules,
                self.all_modules, self.databases))
        except (xmlrpc.client.Fault, TimeoutError) as e:
            raise ValidationError(e)

    def _extract_databases(self, db_name_string):
        """
        Extrae de una cadena de texto con nombres de bases de datos separadas por coma, los nombres a un listado.
        :return: None
        """
        if db_name_string:
            self.databases = [name.strip() for name in db_name_string.split(',')]

    def _make_lic_files(self):
        """
        Crea los ficheros encriptados con la información de la licencia.
        :return: None
        """

        self._set_locations()
        # Esta función va primero pues establece las rutas para almacenar los restantes archivos.
        prev_locations = self._assign_locations()
        lic_info = {'expiration_date': self.expiration_date.strftime('%Y-%m-%d'),
                    'active_collaborators': self.active_collaborators,
                    'databases': self.databases}
        lic_info.update(self._get_server_info())
        json_string = json.dumps(lic_info)
        self.encrypt(self.lic_file_loc, json_string)
        json_string = json.dumps({'devices': self.devices})
        self.encrypt(self.dev_file_loc, json_string)
        json_string = json.dumps({'modules': self.modules, 'all': self.all_modules})
        self.encrypt(self.apps_file_loc, json_string)

        # Si ocurrió un cambio de la ruta de los archivos de licencia elimino los ficheros en la ruta antigua.
        # for key, value in prev_locations.items():
        #     os.remove(value)

    def validate_license(self, active_db):
        """
        Valida que la licencia no haya expirado y que la verificación de las medidas de seguridad sea correcta.
        :return: True si la licencia no ha expirado o False en caso contrario
        """
        expiration_date = self.get_expiration_date()
        comparison_date = dt.datetime.today()
        databases = self.get_databases()

        errormsg = None
        db_check = active_db in databases if databases else True
        if not db_check:
            errormsg = _("Your current database ({}) is not supported by this license. Supported databases are: {}"
                         ).format(active_db, ', '.join(databases))
        expiration_check = expiration_date >= comparison_date
        if not expiration_check:
            errormsg = _('Your license has expired. Please contact the service provider for a renewal.')

        counters_check = self.validate_security_counters()
        if not counters_check:
            errormsg = _('There is a problem with your license files. Please contact the service provider.')

        return counters_check and expiration_check and db_check, errormsg

    def validate_security_counters(self):
        # Valido que la información almacenada sobre el servidor coincida con la real.
        serial = self.my_licenses.get_machine_sn()
        mac = self.my_licenses.get_mac_addr()
        if self.my_licenses.platform != platform.platform() or self.my_licenses.mac != mac or \
                self.my_licenses.sn != serial:
            return False

        executions = self.my_licenses.get_executions()
        dates = self.my_licenses.get_dates()

        # Valido que la cantidad de ejecuciones se corresponda con la cantidad de fechas almacenadas.
        if executions > 0 and len(dates) == executions:
            # Obtenco la fecha del último login y le resto algo de tiempo para evitar problemas con cambios horarios.
            last_login = dt.datetime.strptime(dates[-1], '%Y-%m-%d %H:%M:%S') - dt.timedelta(hours=2)
            # Finalmente valido que la fecha del último login sea anterior a la fecha de hoy.
            if last_login < dt.datetime.today():
                return True
        return False

    def increment_counters(self):
        """
        Adiciona la fecha actual al listado de fechas e incrementa el contador de ejecuciones en uno. Actualiza los
        ficheros correspondientes.
        :return: None
        """
        self.my_licenses.increment_counters()

    def update_res_config_params(self, set_param):
        # Actualizo el parámetro del sistema con la nueva fecha. (Solo para mostrar el valor en la configuración.)
        set_param("license.expiring.date", self.get_expiration_date(as_str=True))
        set_param("license.max.active.employees", self.get_max_employees())
        set_param("license.nukleo.version", self.get_nukleo_version())
        set_param("license.devices", json.dumps(self.get_devices()))
        set_param("license.apps", json.dumps(self.get_apps_tradename()))
