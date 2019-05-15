from os.path import isfile
from dateutil import parser
import logging as log
from datetime import datetime
import requests
import xml.etree.ElementTree as ET
import pandas as pd

import oricura.sources as sources

_IOF_NS = {'iof': 'http://www.orienteering.org/datastandard/3.0'}


class Loader:

    def __init__(self, config):
        self.config = config
        self.df = None

    def download_xml(self, idgara, force=False):
        url_getter = getattr(sources, self.config['source'])
        remote_url = url_getter(idgara)
        log.debug(remote_url)
        local_file = "data/%s.xml" % str(idgara)
        if not isfile(local_file) or force:
            r = requests.get(remote_url)
            if r.status_code == 200 and r.headers['content-type'] == 'text/xml':
                with open(local_file, 'wb') as f:
                    f.write(r.content)
                log.info("Downloaded results for " + str(idgara))
            else:
                log.debug(r.headers['content-type'])
                log.warning("Failed to download results for %s" % str(idgara))
        else:
            log.info("Results for " + str(idgara) + " in cache")

    def download_xmls(self, force=False):
        for id_gara, date in self.config['gare'].values():
            if parser.parse(date, dayfirst=True) < datetime.now():
                self.download_xml(id_gara, force=force)

    @staticmethod
    def xml_to_df(xmlfile):
        tree = ET.parse(xmlfile)
        results = []
        date = tree.find('iof:Event/iof:StartTime/iof:Date', _IOF_NS).text
        for classresult in tree.findall('iof:ClassResult', _IOF_NS):
            classname = classresult.find('iof:Class', _IOF_NS).find('iof:Id', _IOF_NS).text
            course_length = classresult.find('iof:Course/iof:Length', _IOF_NS).text
            course_climb = classresult.find('iof:Course/iof:Climb', _IOF_NS).text

            for pers_res in classresult.findall('iof:PersonResult', _IOF_NS):
                person = pers_res.find('iof:Person', _IOF_NS)
                organisation = pers_res.find('iof:Organisation', _IOF_NS)
                try:
                    entry = dict(
                        classname=classname,
                        course_length=course_length,
                        course_climb=course_climb,
                        person_id=pers_res.find('iof:Person/iof:Id', _IOF_NS).text,
                        name=(person.find('iof:Name/iof:Family', _IOF_NS).text or " ") + ", " + (
                                person.find('iof:Name/iof:Given', _IOF_NS).text or " "),
                        organisation_id=organisation.find('iof:Id', _IOF_NS).text,
                        organisation_name=organisation.find('iof:Name', _IOF_NS).text,
                        organisation_country=organisation.find('iof:Country', _IOF_NS).get('code'),
                        time=pers_res.find('iof:Result/iof:Time', _IOF_NS).text,
                        time_behind=pers_res.find('iof:Result/iof:TimeBehind', _IOF_NS).text,
                        position=pers_res.find('iof:Result/iof:Position', _IOF_NS).text,
                        status=pers_res.find('iof:Result/iof:Status', _IOF_NS).text,
                    )
                    results += [entry]
                except AttributeError:
                    entry = dict(
                        classname=classname,
                        course_length=course_length,
                        course_climb=course_climb,
                        person_id=pers_res.find('iof:Person/iof:Id', _IOF_NS).text,
                        name=(person.find('iof:Name/iof:Family', _IOF_NS).text or " ") + ", " + (
                                person.find('iof:Name/iof:Given', _IOF_NS).text or " "),
                        # organisation_id=organisation.find('iof:Id', _iofns).text,
                        # organisation_name=organisation.find('iof:Name', _iofns).text,
                        # organisation_country=organisation.find('iof:Country', _iofns).get('code'),
                        time=pers_res.find('iof:Result/iof:Time', _IOF_NS).text,
                        time_behind=pers_res.find('iof:Result/iof:TimeBehind', _IOF_NS).text,
                        position=pers_res.find('iof:Result/iof:Position', _IOF_NS).text,
                        status=pers_res.find('iof:Result/iof:Status', _IOF_NS).text,
                    )
                    results += [entry]
        res = pd.DataFrame(results)
        res.time = pd.to_numeric(res.time)
        res['Date'] = date
        return res

    def make_dataframe(self):
        config = self.config
        df = None
        for garaname in config['gare']:
            id_gara, date = config['gare'][garaname]
            local_file = "data/%s.xml" % str(id_gara)
            if isfile(local_file):
                df2 = Loader.xml_to_df(open(local_file))
                df2['garaname'] = garaname
                df2['garaid'] = id_gara
                df2['date'] = parser.parse(date)
                if df is None:
                    df = df2
                else:
                    df = df.append(df2, ignore_index=True)
        df.name = df.name.apply(lambda x: x.split(',')[0].upper() + ', ' + x.split(', ')[1].title())
        try:
            for oldname, newname in config['fixes'].items():
                df.replace(oldname, newname, inplace=True)
        except AttributeError:
            pass

        self.df = df.query("status != 'DidNotStart'")
        return self.df

    def load(self):
        self.download_xmls()
        self.make_dataframe()
        return self.df
