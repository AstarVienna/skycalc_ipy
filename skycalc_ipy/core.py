"""skycalc Module
Taken from the skycalc_cli version 1.0 installation file
"""

from __future__ import print_function
import sys
import json
from datetime import datetime
import requests
import pkg_resources
import getopt

import numpy as np


class AlmanacQuery:
    """AlmanacQuery for Querying the SkyCalc Almanac"""

    def __init__(self, indic):

        self.almdata = None
        self.almserver = 'http://etimecalret-001.eso.org'
        self.almurl = '/observing/etc/api/skycalc_almanac'

        # Left: users keyword (skycalc_cli),
        # Right: skycalc Almanac output keywords
        self.alm_parameters = {}
        self.alm_parameters['airmass'] = 'target_airmass'
        self.alm_parameters['msolflux'] = 'sun_aveflux'
        self.alm_parameters['moon_sun_sep'] = 'moon_sun_sep'
        self.alm_parameters['moon_target_sep'] = 'moon_target_sep'
        self.alm_parameters['moon_alt'] = 'moon_alt'
        self.alm_parameters['moon_earth_dist'] = 'moon_earth_dist'
        self.alm_parameters['ecl_lon'] = 'ecl_lon'
        self.alm_parameters['ecl_lat'] = 'ecl_lat'
        self.alm_parameters['observatory'] = 'observatory'

        self.almindic = {}
        # The Almanac needs:
        # coord_ra      : float [deg]
        # coord_dec     : float [deg]
        # input_type    : ut_time | local_civil_time | mjd
        # mjd           : float
        # coord_year    : int
        # coord_month   : int
        # coord_day     : int
        # coord_ut_hour : int
        # coord_ut_min  : int
        # coord_ut_sec  : float

        if 'date' in indic:
            self.almindic['input_type'] = 'ut_time'
            isotime = None
            try:
                isotime = datetime.strptime(indic['date'],
                                            '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                print('Error: wrong date format for the Almanac.')
                raise
            self.almindic['coord_year'] = isotime.year
            self.almindic['coord_month'] = isotime.month
            self.almindic['coord_day'] = isotime.day
            self.almindic['coord_ut_hour'] = isotime.hour
            self.almindic['coord_ut_min'] = isotime.minute
            self.almindic['coord_ut_sec'] = isotime.second

        elif 'mjd' in indic:
            self.almindic['input_type'] = 'mjd'
            mjd = None
            try:
                mjd = float(indic['mjd'])
            except ValueError:
                print('Error: wrong mjd format for the Almanac.')
                raise
            self.almindic['mjd'] = mjd

        else:
            raise ValueError('Error: no date or mjd given for the Almanac')

        if 'ra' not in indic:
            raise ValueError('Error: ra coordinate not given for the Almanac.')

        if 'dec' not in indic:
            raise ValueError('Error: dec coordinate '
                             'not given for the Almanac.')

        ra = None
        try:
            ra = float(indic['ra'])
        except ValueError:
            print('Error: wrong ra format for the Almanac.')
            raise
        self.almindic['coord_ra'] = ra

        dec = None
        try:
            dec = float(indic['dec'])
        except ValueError:
            print('Error: wrong dec format for the Almanac.')
            raise
        self.almindic['coord_dec'] = dec

        if 'observatory' in indic:
            self.almindic['observatory'] = indic['observatory']

    def query(self):

        url = self.almserver + self.almurl

        rawdata = None
        try:
            response = requests.post(url, json.dumps(self.almindic))
            rawdata = response.text
        except requests.exceptions.RequestException as e:
            print('Error: Almanac query failed.')
            raise

        # Process rawdata
        jsondata = None
        try:
            jsondata = json.loads(rawdata)
            jsondata = jsondata['output']
        except (KeyError, ValueError):
            print('Error: invalid Almanac response.')
            raise

        # Find the relevant (key, value)
        almdata = {}
        for key, value in self.alm_parameters.items():
            subsection = 'nothing'
            prefix = value.split('_')[0]
            if prefix == 'sun' or prefix == 'moon' or prefix == 'target':
                subsection = prefix
            elif prefix == 'ecl':
                subsection = 'target'
            else:
                subsection = 'observation'
            try:
                almdata[key] = jsondata[subsection][value]
            except (KeyError, ValueError):
                print('Warning: key "' + subsection + '/' + value +
                      '" not found in the Almanac response.')

        return almdata


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class SkyModel:
    """SkyModel for querying the Advanced SkyModel"""

    def __init__(self):

        self.stop_on_errors_and_exceptions = True
        self.data = None
        self.server = 'http://etimecalret-001.eso.org'
        self.url = self.server + '/observing/etc/api/skycalc'
        self.deleter_script_url = self.server + '/observing/etc/api/rmtmp'
        self.bugreport_text = ''
        self.tmpdir = ''
        self.params = {
            # Airmass. Alt and airmass are coupled through the plane parallel
            # approximation airmass=sec(z), z being the zenith distance
            # z=90−Alt
            'airmass': 1.0,    # float range [1.0,3.0]

            # Season and Period of Night
            'pwv_mode': 'pwv',  # string  grid ['pwv','season']
            # integer grid [0,1,2,3,4,5,6] (0=all year, 1=dec/jan,2=feb/mar...)
            'season': 0,
            # third of night integer grid [0,1,2,3] (0=all year, 1,2,3 = third
            # of night)
            'time': 0,

            # Precipitable Water Vapor PWV
            # mm float grid [-1.0,0.5,1.0,1.5,2.5,3.5,5.0,7.5,10.0,20.0]
            'pwv': 3.5,

            # Monthly Averaged Solar Flux
            'msolflux': 130.0,  # s.f.u float > 0

            # Scattered Moon Light
            # Moon coordinate constraints: |z – zmoon| ≤ ρ ≤ |z + zmoon| where
            # ρ=moon/target separation, z=90°−target altitude and
            # zmoon=90°−moon altitude.
            # string grid ['Y','N'] flag for inclusion of scattered moonlight.
            'incl_moon': 'Y',
            # degrees float range [0.0,360.0] Separation of Sun and Moon as
            # seen from Earth ("moon phase")
            'moon_sun_sep': 90.0,
            # degrees float range [0.0,180.0] Moon-Target Separation ( ρ )
            'moon_target_sep': 45.0,
            # degrees float range [-90.0,90.0] Moon Altitude over Horizon
            'moon_alt': 45.0,
            # float range [0.91,1.08] Moon-Earth Distance (mean=1)
            'moon_earth_dist': 1.0,

            # Starlight
            # string  grid ['Y','N'] flag for inclusion of scattered starlight
            'incl_starlight': 'Y',

            # Zodiacal light
            # string grid ['Y','N'] flag for inclusion of zodiacal light
            'incl_zodiacal': 'Y',
            # degrees float range [-180.0,180.0] Heliocentric ecliptic
            # longitude
            'ecl_lon': 135.0,
            # degrees float range [-90.0,90.0] Ecliptic latitude
            'ecl_lat': 90.0,

            # Molecular Emission of Lower Atmosphere
            # string grid ['Y','N'] flag for inclusion of lower atmosphere
            'incl_loweratm': 'Y',
            # Emission Lines of Upper Atmosphere
            # string grid ['Y','N'] flag for inclusion of upper stmosphere
            'incl_upperatm': 'Y',
            # Airglow Continuum (Residual Continuum)
            # string grid ['Y','N'] flag for inclusion of airglow
            'incl_airglow': 'Y',

            # Instrumental Thermal Emission This radiance component represents
            # an instrumental effect. The emission is provided relative to the
            # other model components. To obtain the correct absolute flux, an
            # instrumental response curve must be applied to the resulting
            # model spectrum See section 6.2.4 in the documentation
            # http://localhost/observing/etc/doc/skycalc/
            # The_Cerro_Paranal_Advanced_Sky_Model.pdf
            # string grid ['Y','N'] flag for inclusion of instrumental thermal
            # radiation
            'incl_therm': 'N',
            'therm_t1': 0.0,   # K float > 0
            'therm_e1': 0.0,   # float range [0,1]
            'therm_t2': 0.0,   # K float > 0
            'therm_e2': 0.0,   # float range [0,1]
            'therm_t3': 0.0,   # float > 0
            'therm_e3': 0.0,   # K float range [0,1]

            # Wavelength Grid
            'vacair': 'vac',  # vac or air
            'wmin': 300.0,  # nm float range [300.0,30000.0] < wmax
            'wmax': 2000.0,  # nm float range [300.0,30000.0] > wmin
            # string grid ['fixed_spectral_resolution','fixed_wavelength_step']
            'wgrid_mode': 'fixed_wavelength_step',
            # nm/step float range [0,30000.0] wavelength sampling step dlam
            # (not the res.element)
            'wdelta': 0.1,
            # float range [0,1.0e6] RESOLUTION is misleading, it is rather
            # lam/dlam where dlam is wavelength step (not the res.element)
            'wres': 20000,

            # Convolve by Line Spread Function
            'lsf_type': 'none',   # string grid ['none','Gaussian','Boxcar']
            'lsf_gauss_fwhm': 5.0,      # wavelength bins float > 0
            'lsf_boxcar_fwhm': 5.0,     # wavelength bins float > 0
            'observatory': 'paranal'    # paranal
        }

    def fixObservatory(self):

        if 'observatory' in indic:
            if self.params['observatory'] == 'lasilla':
                self.params['observatory'] = '2400'
            elif self.params['observatory'] == 'paranal':
                self.params['observatory'] = '2640'
            elif (self.params['observatory'] == '3060m' or
                  self.params['observatory'] == 'armazones'):
                self.params['observatory'] = '3060'
            elif self.params['observatory'] == '5000m':
                self.params['observatory'] = '5000'
            else:
                raise ValueError('Wrong Observatory name, please refer to the '
                                 'documentation.')


    def validate_params(self):
        p = self.params

        self.fixObservatory()

        msgs = []
        if p["airmass"] < 1.0 or p["airmass"] > 3.0:
            msgs += ["airmass must be in the range [1.0, 3.0]"]

        if p["pwv_mode"] not in ['pwv','season']:
            msgs += ["pwv_mode must be in ['pwv','season']"]

        if type(p["season"]) is not int and \
                (p["season"] > 6 or p["season"] < 0):
            msgs += ["season must be an integer in the range [0, 6]."]

        if type(p["time"]) is not int and \
                (p["time"] > 3 or p["season"] < 0):
            msgs += ["time must be an integer in the range [0, 3]."]

        if p["pwv"] < -1 or p["pwv"] > 20.:
            msgs += ["pwv must be in the range [-1.0, 20.0]."]
        else:
            pwv_grid = np.array([-1., 0.5, 1., 1.5, 2.5, 3.5, 5., 7.5, 10., 20.])
            ii = np.argmin(np.abs(pwv_grid - p["pwv"]))
            p["pwv"] = pwv_grid[ii]

        if p["msolflux"] < 0.:
            msgs += ["msolflux must be greater than 0"]

        if p["incl_moon"] not in ["Y", "N"]:
            msgs += ["incl_moon must be 'Y' or 'N'"]

        if p["moon_sun_sep"] < 0. or p["moon_sun_sep"] > 360.:
            msgs += ["moon_sun_sep must be in the range [0, 360]"]

        if p["moon_target_sep"] < 0. or p["moon_target_sep"] > 180.:
            msgs += ["moon_target_sep must be in the range [0, 180]"]

        if p["moon_alt"] < 90. or p["moon_alt"] > 90.:
            msgs += ["moon_alt must be in the range [-90, 90]"]

        if p["moon_earth_dist"] < 0.91 or p["moon_earth_dist"] > 1.08:
            msgs += ["moon_earth_dist must be in the range [0.91, 1.08]"]

        if p["incl_starlight"] not in ["Y", "N"]:
            msgs += ["incl_starlight must be 'Y' or 'N'"]

        if p["incl_zodiacal"] not in ["Y", "N"]:
            msgs += ["incl_zodiacal must be 'Y' or 'N'"]

        if p["ecl_lon"] < -180. or p["ecl_lon"] > 180.:
            msgs += ["ecl_lon must be in the range [-180, 180]"]

        if p["ecl_lat"] < -90. or p["ecl_lat"] > 90.:
            msgs += ["ecl_lat must be in the range [-90, 90]"]

        if p["incl_loweratm"] not in ["Y", "N"]:
            msgs += ["incl_loweratm must be 'Y' or 'N'"]

        if p["incl_upperatm"] not in ["Y", "N"]:
            msgs += ["incl_upperatm must be 'Y' or 'N'"]

        if p["incl_airglow"] not in ["Y", "N"]:
            msgs += ["incl_airglow must be 'Y' or 'N'"]

        if p["incl_therm"] not in ["Y", "N"]:
            msgs += ["incl_therm must be 'Y' or 'N'"]

        for param in ["therm_t1", "therm_t2", "therm_t3"]:
            if p[param] < 0:
                msgs += [param + " must be >= 0"]

        for param in ["therm_e1", "therm_e2", "therm_e3"]:
            if p[param] < 0 or p[param] > 1:
                msgs += [param + " must be in the range [0, 1]"]

        if p["vacair"] not in ["vac", "air"]:
            msgs += ["vacair must be 'vac' or 'air'"]

        if p["wmin"] < 300. or p["wmin"] > 30000.:
            msgs += ["wmin must be in the range [-300, 30000]"]

        if p["wmax"] < -300. or p["wmax"] > 30000.:
            msgs += ["wmax must be in the range [-300, 30000]"]

        if p["wmax"] < p["wmin"]:
            msgs += ["wmax must be greater than wmin"]

        if p["wgrid_mode"] not in ['fixed_spectral_resolution',
                                   'fixed_wavelength_step']:
            msgs += ["wgrid_mode must be 'fixed_spectral_resolution' or "
                                        "'fixed_wavelength_step'"]

        if p["wdelta"] < 0. or p["wdelta"] > 30000.:
            msgs += ["wdelta must be in the range [0, 30000]"]

        if p["wres"] < 0. or p["wres"] > 1E6:
            msgs += ["wres must be in the range [0, 1E6]"]

        if p["lsf_type"] not in ['none','Gaussian','Boxcar']:
            msgs += ["lsf_type must one of ['none','Gaussian','Boxcar']"]

        if p["lsf_gauss_fwhm"] < 0.:
            msgs += ["lsf_gauss_fwhm must be greater than 0"]

        if p["lsf_boxcar_fwhm"] < 0.:
            msgs += ["lsf_boxcar_fwhm must be greater than 0"]





        if len(msgs) > 0:
            msgs += ["Call <SkyModel>.help(<keyword>) for the allowed values"]


    def help(self):
        return False
        

    def __getitem__(self, item):
        return self.params[item]

    def __setitem__(self, key, value):
        self.params[key] = value
        if key == "observatory":
            self.fixObservatory()

    def handle_exception(self, e, msg):
        print(msg)
        print(e)
        print(self.bugreport_text)
        if(self.stop_on_errors_and_exceptions):
            sys.exit()

    # handle the kind of errors we issue ourselves.
    def handle_error(self, msg, stop=True):
        print(msg)
        print(self.bugreport_text)
        if(self.stop_on_errors_and_exceptions):
            sys.exit()

    def retrieve_data(self, url):
        try:
            response = requests.get(url, stream=True)
            self.data = response.content
        except requests.exceptions.RequestException as e:
            self.handle_exception(
                e, 'Exception raised trying to get FITS data from ' + url)

    def write(self, local_filename):
        try:
            with open(local_filename, 'wb') as f:
                f.write(self.data)
        except IOError as e:
            self.handle_exception(
                e, 'Exception raised trying to write fits file ')

    def getdata(self):
        return self.data

    def delete_server_tmpdir(self, tmpdir):
        try:
            response = requests.get(self.deleter_script_url + '?d=' + tmpdir)
            deleter_response = response.text.strip()
            if(deleter_response != 'ok'):
                self.handle_error('Could not delete server tmpdir ' + tmpdir)
        except requests.exceptions.RequestException as e:
            self.handle_exception(
                e, 'Exception raised trying to delete tmp dir ' + tmpdir)

    def call(self, test=False):
        # print 'self.url=',self.url
        # print 'self.params=',self.params
        try:
            response = requests.post(self.url, data=json.dumps(self.params))
        except requests.exceptions.RequestException as e:
            self.handle_exception(
                e, 'Exception raised trying to POST request ' + self.url)
        try:
            res = json.loads(response.text)
            status = res['status']
            tmpdir = res['tmpdir']
        except (KeyError, ValueError) as e:
            self.handle_exception(
                e, 'Exception raised trying to decode server response ')

        tmpurl = self.server + '/observing/etc/tmp/' + \
            tmpdir + '/skytable.fits'

        if(status == 'success'):
            try:
                # retrive and save FITS data (in memory)
                self.retrieve_data(tmpurl)
            except requests.exceptions.RequestException as e:
                self.handle_exception(
                    e, 'could not retrieve FITS data from server')

            self.delete_server_tmpdir(tmpdir)

        else:  # print why validation failed
            self.handle_error('parameter validation error: ' +
                              res['error'])

        if(test):
            # print 'call() returning status:',status
            return status

    def callwith(self, newparams):
        for key, val in newparams.items():
            if key in self.params:  # valid
                self.params[key] = val
            else:  # invalid
                print('callwith() ignoring invalid keyword: ', key)
        self.call()

    def printparams(self, keys=None):
        if keys is None:
            p = self.params
        else:
            p = dict((k, self.params[k]) for k in keys if k in self.params)
        for k in p:
            print(k, p[k])

    def test(self, label, overwite_params):
        from cStringIO import StringIO

        # capture stdout for a while
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()

        sm = SkyModel()
        str_params = ''
        # replace all matching keywords with the values in the newdict
        for key, val in overwite_params.items():
            if key in sm.params:
                sm.params[key] = val
                str_params = str_params + str(key) + ' : ' + str(val) + ', '
        status = sm.call(True)  # set True for test

        # restore original stdout
        sys.stdout = old_stdout
        toprint = label + '\t'
        # print str_params
        if(status == 'success'):
            toprint += bcolors.OKGREEN + ' *** pass *** ' + bcolors.ENDC
        else:
            toprint += bcolors.FAIL + ' *** fail *** ' + bcolors.ENDC
        print(toprint)

        print(mystdout.getvalue())

    def reset(self):
        self.__init__()


######################################
# Beginning of skycalc_cli.py
######################################

def loadTxt(inputFile):

    result = {}

    lineN = 0
    for line in inputFile.readlines():

        lineN += 1

        originalLine = line
        line = line.strip()
        if len(line) == 0 or line[0] == '#':
            continue
        line = line.split(':')
        if len(line) > 2 and line[0].strip() == 'date':
            line = [line[0], ':'.join(line[1::])]
        elif len(line) != 2 or (len(line) == 2 and (line[0].strip() == '' or
                                                    line[1].strip() == '')):
            print('WARNING: input file line ' + str(lineN) +
                  ': wrong format: ignored.')
            print(originalLine.rstrip())
            continue
        key = line[0].strip()
        value = line[1].strip()

        # Is it an integer?
        try:
            value = int(value)
        except ValueError:
            # Is it an float?
            try:
                value = float(value)
            except ValueError:
                pass

        result[key] = value

    return result


def main():

    argv = sys.argv[1:]

    almFilename = None
    inputFilename = None
    outputFilename = None
    isVerbose = False

    # Read command line arguments
    try:
        opts, args = getopt.getopt(argv, "hva:i:o:", ["help", "verbose",
                                                      "version",
                                                      "alm=", "in=", "out="])
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("--version"):
            version = pkg_resources.require("skycalc_cli")[0].version
            print('skycalc_cli version ' + version)
            sys.exit(0)
        elif opt in ("-v", "--verbose"):
            isVerbose = True
        elif opt in ("-a", "--alm"):
            almFilename = arg
        elif opt in ("-i", "--in"):
            inputFilename = arg
        elif opt in ("-o", "--out"):
            outputFilename = arg

    if not ((inputFilename or almFilename) and outputFilename):
        usage()
        sys.exit(1)

    dic = {}

    # Query the Almanac if alm option is enabled
    if almFilename:

        # Read the input parameters
        inputalmdic = None
        try:
            with open(almFilename, 'r') as f:
                inputalmdic = json.load(f)
        except ValueError:
            with open(almFilename, 'r') as f:
                inputalmdic = loadTxt(f)

        if not inputalmdic:
            raise ValueError('Error: cannot read' + almFilename)

        alm = AlmanacQuery(inputalmdic)
        dic = alm.query()

    if isVerbose:
        print('Data retrieved from the Almanac:')
        for key, value in dic.items():
            print('\t' + str(key) + ': ' + str(value))

    if inputFilename:

        # Read input parameters
        inputdic = None
        try:
            with open(inputFilename, 'r') as f:
                inputdic = json.load(f)
        except ValueError:
            with open(inputFilename, 'r') as f:
                inputdic = loadTxt(f)

        if not inputdic:
            raise ValueError('Error: cannot read ' + inputFilename)

        # Override input parameters
        if isVerbose:
            print('Data overridden by the user\'s input file:')
        for key, value in inputdic.items():
            if isVerbose and key in dic:
                print('\t' + str(key) + ': ' + str(value))
            dic[key] = value

    # Fix the observatory to fit the backend
    try:
        dic = fixObservatory(dic)
    except ValueError:
        raise

    if isVerbose:
        print('Data submitted to SkyCalc:')
        for key, value in dic.items():
            print('\t' + str(key) + ': ' + str(value))

    # Get the Sky
    skyModel = SkyModel()
    skyModel.callwith(dic)
    skyModel.write(outputFilename)
