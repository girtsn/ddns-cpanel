"""cpanel ddns implementation"""

import logging
import json
import argparse
from datetime import datetime
from dateutil import tz

try:
    # python 3
    from urllib.request import urlopen, Request
    from urllib.parse import urlencode
except ImportError:
    # python 2
    from urllib import urlencode
    from urllib2 import urlopen, Request

def timetz(*args):
    return datetime.now(tzz).timetuple()

def _get_zone_and_name(base_url, base_headers, base_data,  domain):
        """Find a suitable zone for a domain
        :param str record_name: the domain name
        :returns: (the zone, the name in the zone)
        :rtype: tuple
        """
        cpanel_zone = ''
        cpanel_name = ''

        data = base_data.copy()
        data['cpanel_jsonapi_func'] = 'fetchzones'

        logger.debug("req fetchzones: url='%s', data='%s'" % (base_url, urlencode(data) ) )
	try:
            response = urlopen(
	        Request(
    	            "%s?%s" % (base_url, urlencode(data)),
        	    headers=base_headers
        	)
    	    )
        except Exception as e:
    	    logger.error('911 req fetchzones failed: %s', e);
    	    exit(1);
    	response_data = json.load(response)['cpanelresult']
        logger.debug("rsp fetchzones: data='%s'" % json.dumps(response_data, indent=4))
        matching_zones = []
        for zone in response_data['data'][0]['zones']:
            if (domain == zone or domain.endswith('.' + zone)):
                matching_zones.append(zone)
        if matching_zones:
            cpanel_zone = min(matching_zones, key = len)
            cpanel_name = domain[:-len(cpanel_zone)-1]
        else:
            logger.error('nohost %s', domain)
            exit(1)

        return (cpanel_zone, cpanel_name)

def _get_record_lines_and_data(base_url, base_headers, base_data, cpanel_zone, record_name, record_type):
        """Find the line numbers of a record a zone
        :param str cpanel_zone: the zone of the record
        :param str record_name: the name in the zone of the record
        :param str record_content: the content of the record
        :param str cpanel_ttl: the ttl of the record
        :returns: the line number and all it's duplicates
        :rtype: list
        """
        record_lines = []

        data = base_data.copy()
        data['cpanel_jsonapi_func'] = 'fetchzone_records'
        data['domain'] = cpanel_zone
        data['name'] = record_name
        data['type'] = record_type

        logger.debug("req fetchzone_records: url='%s', data='%s'" % (base_url, urlencode(data) ) )
	try:
            response = urlopen(
	        Request(
    	            "%s?%s" % (base_url, urlencode(data)),
    	            headers=base_headers
        	    )
    	    )
	except Exception as e:
	    logger.error('911 req fetchzone_records failed: %s', e);
	    exit(1);
        response_data = json.load(response)['cpanelresult']
        logger.debug("rsp fetchzone_records: data='%s'" % json.dumps(response_data, indent=4))
        record_lines = [int(d['line']) for d in response_data['data']]

        return (record_lines, response_data['data'])

# some guidance on what to return: https://help.dyn.com/remote-access-api/return-codes/

if __name__ == "__main__":

    tzz = tz.gettz('UTC')

    logging.Formatter.converter = timetz

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler('ddns-py.log')
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARN)
    formatter2 = logging.Formatter('%(message)s')
    ch.setFormatter(formatter2)
    logger.addHandler(ch)

    try:
        from ddns_config import CONFIG
    except ImportError:
        logger.error("911 Error: ddns-config.py NOT found")
        exit()

    tzz = tz.gettz(CONFIG['timezone'])

    logging.Formatter.converter = timetz

    # Show all arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--record_ttl', default='300', help='Time To Live')
    parser.add_argument('--record_type', default='A', help='Type of record: A for IPV4 or AAAA for IPV6')
    parser.add_argument('--ip', help='The IPV4/IPV6 address', required=True)
    parser.add_argument('--record_name', help='Your record name, e.g.: subdomain.', required=True)
    parser.add_argument('--domain', help='Your domain, e.g.. example.com', required=True)
    parser.add_argument('--v', action='store', nargs='*', help="Debug loglevels")
    try:
	args = parser.parse_args()
    except Exception as e:
	logger.error('911 argumentg parsing failed: %s', e);
	exit(1);

    if (args.v != None):
        ch.setLevel(logging.DEBUG)
        logger.warn('enabling debug logging')
        

    base_url = "%s/json-api/cpanel" % CONFIG['url']
    base_data = {
            'cpanel_jsonapi_user': CONFIG['username'],
            'cpanel_jsonapi_apiversion': '2',
            'cpanel_jsonapi_module': 'ZoneEdit'
    }

    base_headers = {
                'Authorization': 'cpanel %s:%s' % (CONFIG['username'], CONFIG['token'])
    }

    logger.debug("domain='%s', record='%s'" % (args.domain, args.record_name) )
    cpanel_zone, cpanel_name = _get_zone_and_name(base_url, base_headers, base_data, args.domain)
    record_lines, exist_data = _get_record_lines_and_data(base_url, base_headers, base_data, cpanel_zone, args.record_name, args.record_type)
    
    if not record_lines:
        data = base_data.copy()
        data['cpanel_jsonapi_func'] = 'add_zone_record'
        data['domain'] = cpanel_zone
        data['name'] = args.record_name
        data['address'] = args.ip
        data['type'] = args.record_type
        data['ttl'] = args.record_ttl

        logger.debug("req add_zone_record: url='%s', data='%s'" % (base_url, urlencode(data) ) )
	try:
            response = urlopen(
	        Request(
    	            "%s?%s" % (base_url, urlencode(data)),
        	    headers=base_headers,
        	)
    	    )
    	except Exception as e:
	    logger.error('911 req add_zpne_record failed: %s', e);
	    exit(1);
        response_data = json.load(response)['cpanelresult']
        logger.debug("rsp add_zone_record: data='%s'" % json.dumps(response_data, indent=4))
        if response_data['data'][0]['result']['status'] == 1:
            logger.info("Successfully added entry for record='%s' ip='%s' type='%s' ttl='%s'", args.record_name, args.ip, args.record_type, args.record_ttl)
            logger.warn("good %s", args.ip)
        else:
            logger.error("911 error adding record: %s" % response_data['data'][0]['result']['statusmsg'])
            exit(1)
    else:
        if (len(record_lines) != 1):
    	    logger.error("911 not exactly one existing record")
    	    exit(1)
    	if (exist_data[0]['address'] == args.ip and  exist_data[0]['type'] == args.record_type and exist_data[0]['ttl'] == args.record_ttl):
    	    logger.warn("nochg %s", args.ip)
    	    exit(0)
        data = base_data.copy()
        data['cpanel_jsonapi_func'] = 'edit_zone_record'
        data['domain'] = cpanel_zone
        data['line'] = record_lines[0]
        data['name'] = args.record_name
        data['address'] = args.ip
        data['type'] = args.record_type
        data['ttl'] = args.record_ttl

        logger.debug("req edit_zone_record: url='%s', data='%s'" % (base_url, urlencode(data) ) )
        try:
            response = urlopen(
	        Request(
    	            "%s?%s" % (base_url, urlencode(data)),
        	    headers=base_headers,
        	)
    	    )
    	except Exception as e:
	    logger.error('911 req edit_zone_record failed: %s', e);
	    exit(1);
        response_data = json.load(response)['cpanelresult']
        logger.debug("rsp edit_zone_record: data='%s'" % json.dumps(response_data, indent=4))
        if response_data['data'][0]['result']['status'] == 1:
            logger.info("Successfully updated entry for record='%s' ip='%s' type='%s' ttl='%s'", args.record_name, args.ip, args.record_type, args.record_ttl)
            logger.warn("good %s", args.ip)
        else:
            logger.error("911 error updating record: %s" % response_data['data'][0]['result']['statusmsg'])
            exit(1)
