#!/usr/bin/python3
import datetime, time
import configparser
import iso8601
import requests
from pytz import timezone
from sys import argv
import sys
sys.path.insert(0, '/home/pi/ME3000')
from me3000 import ME3000
from MyME3000 import *


def MyConfiguration():
    file = 'agile.cfg')
    parser = configparser.ConfigParser()
    parser.optionxform = str  # make option names case sensitive
    found = parser.read(file)
    if not found:
        raise ValueError('No config file found!')
    return parser


uk_tz = timezone('Europe/London')
cfg = MyConfiguration()


class AgileTariff:
    def __init__(self, tariff_):
        now = datetime.datetime.now().astimezone(uk_tz)
        self.hour = datetime.timedelta(hours=1)
        self.day = datetime.timedelta(days=1)
        self.zero = dict(minute=0, second=0, microsecond=0)
        self.halfhour = dict(minute=30, second=0, microsecond=0)
        self.midnight = dict(hour=0, minute=0, second=0, microsecond=0)
        self.ratestart = self.round_to_low_30min(now)
        self.rateend = self.ratestart + datetime.timedelta(minutes=30)
        self.ratedata = self.agile_store_two_days(tariff_)
        self.currentrate = self.get_currentrate(tariff_)

    def agile_store_two_days(self, tariff_):
        now = datetime.datetime.now().astimezone(uk_tz)
        zerohour = now.replace(**self.midnight)
        thisrates = tariff_.agile_tariff_unit_rates(
                                                 period_from=zerohour,
                                                 period_to=zerohour + self.day + self.day)
        data = {}
        for k in thisrates['results']:
            unitprice = k['value_inc_vat']
            ufrom = iso8601.parse_date(str(k['valid_from'])).astimezone(uk_tz)
            # uto = iso8601.parse_date(str(k['valid_to'])).astimezone(uk_tz)
            data[ufrom] = unitprice
        return data

    def return_todays_values_between(self, thisstart, thisend):  #
        zeroedstart = self.round_to_low_30min(thisstart)
        times = {}
        for thisdate, thisprice in self.ratedata.items():
            if zeroedstart < thisdate < thisend:
                times[thisdate] = thisprice
        return times

    def get_currentrate(self, tariff_):
        now = datetime.datetime.now().replace(second=0, microsecond=0).astimezone(uk_tz)
        self.ratestart = self.round_to_low_30min(now)
        self.rateend = self.ratestart + datetime.timedelta(minutes=30)

        if self.ratestart not in self.ratedata:  # refresh data if current period does not exist
            self.ratedata = self.agile_store_two_days(tariff_)

        self.currentrate = self.ratedata[self.ratestart]
        print('New tariff rate - Start: {:%H:%M} End: {:%H:%M} Price:{:2.2f}p'.format(
            self.ratestart,
            self.rateend,
            self.currentrate))
        return self.currentrate

    def round_to_low_30min(self, now):
        if now.minute >= 30:
            return now.replace(**self.halfhour)
        else:
            return now.replace(**self.zero)


class APIClient(object):
    # https://gist.github.com/codeinthehole/5f274f46b5798f435e6984397f1abb64
    # https://developer.octopus.energy/docs/api/

    class DataUnavailable(Exception):
        """
        Catch-all exception indicating we can't get data back from the API
        """

    def __init__(self):
        self.api_key = cfg['octopus']['api_key']
        self.BASE_URL = cfg['octopus']['api_url']
        self.gsp = str(cfg['octopus']['region']).upper()
        self.serial = cfg['octopus']['serial_no']
        self.session = requests.Session()

    def _get(self, path, params=None):
        """
        Make a GET HTTP request
        """
        if params is None:
            params = {}
        url = self.BASE_URL + path
        try:
            response = self.session.request(
                method="GET", url=url, auth=(self.api_key, ""), params=params)
        except requests.RequestException as e:
            raise self.DataUnavailable("Network exception") from e

        if response.status_code != 200:
            raise self.DataUnavailable("Unexpected response status (%s)" % response.status_code)
        print('Tariff api aquired {} bytes'.format(len(response.json())))
        return response.json()

    def agile_tariff_unit_rates(self, period_from=None, period_to=None):
        """
        Helper method to easily look-up the electricity unit rates for given GSP
        """
        # Handle GSPs passed with leading underscore
        if len(self.gsp) == 2:
            self.gsp = self.gsp[1]
        assert self.gsp in ("A", "B", "C", "D", "E", "F", "G", "P", "N", "J", "H", "K", "L", "M")

        return self.electricity_tariff_unit_rates(
            product_code="AGILE-18-02-21",
            tariff_code="E-1R-AGILE-18-02-21-%s" % self.gsp,
            period_from=period_from,
            period_to=period_to)

    def electricity_tariff_unit_rates(self, product_code, tariff_code, period_from=None, period_to=None):
        # See https://developer.octopus.energy/docs/api/#list-tariff-charges
        params = {}
        if period_from:
            params['period_from'] = period_from.isoformat()
            if period_to:
                params['period_to'] = period_to.isoformat()
        return self._get("/products/%s/electricity-tariffs/%s/standard-unit-rates/" % (
            product_code, tariff_code), params=params)


class ThirtyMinRounder:
    def __init__(self):
        self.hour_ = datetime.timedelta(hours=1)
        self.zero_ = dict(minute=0, second=0, microsecond=0)
        self.halfhour_ = dict(minute=30, second=0, microsecond=0)
        self.now_ = datetime.datetime.now().astimezone(uk_tz)
        self.next_ = self.now_
        if self.now_.minute <= 30:
            self.next_ = self.now_.replace(**self.halfhour_)
        else:
            self.next_ = self.now_.replace(**self.zero_) + self.hour_

    def check(self):
        if self.now_ <= self.next_:
            return False
        return True

def Sofar_to_manual_charge():
    threshold = int(cfg['sofar']['threshold'])
    if threshold < 20 or threshold > 100:
        threshold = 100

    roo = ME3000 (SERIAL_PORT, SLAVE)

    print("Charge threshold =", threshold)
    print("Get inverter state ...")
    status, invstate, invstring = roo.get_inverter_state ()
    if status:
        print("State = ", invstate, "[", invstring, "]")

    print("Get battery percentage ...")
    status, response = roo.get_battery_percentage ()
    if status:
        print(response)
        if response < threshold:
            charge_rate = int(cfg['sofar']['charge_rate'] # todo - maybe vary charge rate

            print("Below threshold, set to charge at", charge_rate)
            status, response = roo.set_charge (charge_rate)
            if status:
                retval = response & 0x00FF
                if retval != 0:
                    print("Set charge failed ...")
        elif invstate == 2 or invstate == 0:
            print("Over threshold and charged, so switch to auto ...")
            status, response = roo.set_auto ()
            if status:
                retval = response & 0x00FF
                if retval != 0:
                    print("Set auto failed", hex (response))

    roo.disconnect ()


def Sofar_to_auto():
    roo = ME3000 (SERIAL_PORT, SLAVE)

    print(datetime.datetime.now())
    print("Get inverter state ...")
    status, invstate, invstring = roo.get_inverter_state ()
    if status:
        print("State = ", invstate, "[", invstring, "]")

    print("Get battery percentage ...")
    status, response = roo.get_battery_percentage ()
    if status:
        print(response)

    print("Set to auto ...")
    retval = -1
    count = 0
    while retval != 0 and count < 100:
        count = count + 1
        status, response = roo.set_auto ()
        if status:
            retval = response & 0x00FF

    if retval != 0:
        print("Set auto failed", hex (response))

    roo.disconnect ()


def main_routine():
    octopus_ = APIClient()
    agile_ = AgileTariff(octopus_)
    # import your SolaxModbusInverters and SolaxBatteryControl here

    print('Agile tariff schedule')
    for thistime, thisprice in agile_.ratedata.items():  # .ratedata is dict (cached api data, will fetch new data)
        tag = ''
        if agile_.ratestart == thistime:
            agile_.currentrate = thisprice
            tag = '<-- You are here'
        print('{:%Y-%m-%d %H:%M} {:2.2f}p {}'.format(thistime, thisprice, tag))
    skip_ = False
    while True:
        global skip_
        now = datetime.datetime.now().astimezone(uk_tz)
        print('\n{:%Y-%m-%d %H:%M:%S} - Tariff now = {}p'.format(now, agile_.currentrate))
        # signed float of current tariff price inc VAT
        low_threshold = float(cfg['tariff']['low_threshold'])

        if agile_.currentrate > 0:  # plunge rate
            Sofar_to_manual_charge()
            skip_ = True
        if agile_.currentrate > low_threshold and not skip_:  # on peak rates
            # Do something with postive value rate
            print('Turn on inverter')
            skip_ = True
            Sofar_to_auto()
        elif agile_.currentrate < low_threshold and not skip_:  # off peak rates
            # Do something with negative value rate
            print('Turn off inverter, turn on charger')
            Sofar_to_manual_charge()
        counter_ = ThirtyMinRounder()
        while not counter_.check():
            time.sleep(1)  # sleep until next 30 min window
        skip_ = False


if __name__ == "__main__":
    main_routine()
