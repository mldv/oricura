from os.path import isfile, basename
import yaml
import pandas as pd
import numpy as np
import requests
import logging as log
from datetime import datetime
from dateutil import parser
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import xml.etree.ElementTree as ET
_iofns = {'iof': 'http://www.orienteering.org/datastandard/3.0'}

log.getLogger().setLevel(log.INFO)

# CONFIG_FILE = 'config/lombardia_sprint_tour_2019.yaml'
CONFIG_FILE = 'config/trofeo_lombardia_2019.yaml'


status = 'DEFINITIVO'


def download_xml(idgara, force=False):
    global status
    remote_url = "https://www.fiso.it/_files/risultati_gara_files/imported/%s.xml" % str(idgara)
    log.debug(remote_url)
    local_file = "data/%s.xml" % str(idgara)
    if not isfile(local_file) or force:
        r = requests.get(remote_url)
        if r.status_code == 200 and r.headers['content-type'] == 'text/xml':
            with open(local_file, 'wb') as f:
                f.write(r.content)
        else:
            status = 'PROVVISORIO'
            log.debug(r.headers['content-type'])
            log.warning("Failed to download results for %s" % str(idgara))


def xml_to_df(xmlfile):
    tree = ET.parse(xmlfile)
    results = []
    date =  tree.find('iof:Event/iof:StartTime/iof:Date', _iofns).text
    for classresult in tree.findall('iof:ClassResult', _iofns):
        classname = classresult.find('iof:Class', _iofns).find('iof:Id', _iofns).text
        course_length = classresult.find('iof:Course/iof:Length', _iofns).text
        course_climb = classresult.find('iof:Course/iof:Climb', _iofns).text

        for pers_res in classresult.findall('iof:PersonResult', _iofns):
            person = pers_res.find('iof:Person', _iofns)
            organisation = pers_res.find('iof:Organisation', _iofns)
            try:
                entry = dict(
                    classname=classname,
                    course_length=course_length,
                    course_climb=course_climb,
                    person_id=pers_res.find('iof:Person/iof:Id', _iofns).text,
                    name=(person.find('iof:Name/iof:Family', _iofns).text or " ") + ", " + (person.find('iof:Name/iof:Given', _iofns).text or " "),
                    organisation_id=organisation.find('iof:Id', _iofns).text,
                    organisation_name=organisation.find('iof:Name', _iofns).text,
                    organisation_country=organisation.find('iof:Country', _iofns).get('code'),
                    time=pers_res.find('iof:Result/iof:Time', _iofns).text,
                    time_behind=pers_res.find('iof:Result/iof:TimeBehind', _iofns).text,
                    position=pers_res.find('iof:Result/iof:Position', _iofns).text,
                    status=pers_res.find('iof:Result/iof:Status', _iofns).text,
                )
                results += [entry]
            except AttributeError:
                entry = dict(
                    classname=classname,
                    course_length=course_length,
                    course_climb=course_climb,
                    person_id=pers_res.find('iof:Person/iof:Id', _iofns).text,
                    name=(person.find('iof:Name/iof:Family', _iofns).text or " ") + ", " + (person.find('iof:Name/iof:Given', _iofns).text or " "),
                    # organisation_id=organisation.find('iof:Id', _iofns).text,
                    # organisation_name=organisation.find('iof:Name', _iofns).text,
                    # organisation_country=organisation.find('iof:Country', _iofns).get('code'),
                    time=pers_res.find('iof:Result/iof:Time', _iofns).text,
                    time_behind=pers_res.find('iof:Result/iof:TimeBehind', _iofns).text,
                    position=pers_res.find('iof:Result/iof:Position', _iofns).text,
                    status=pers_res.find('iof:Result/iof:Status', _iofns).text,
                )
                results += [entry]
    res = pd.DataFrame(results)
    res.time = pd.to_numeric(res.time)
    res['Date'] = date
    return res


def make_dataframe(config):
    df = None
    for garaname in config['gare']:
        id_gara, date = config['gare'][garaname]
        local_file = "data/%s.xml" % str(id_gara)
        if isfile(local_file):
            df2 = xml_to_df(open(local_file))
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

    return df.query("status != 'DidNotStart'")


def cambio_categoria(data, cambi):
    if cambi:
        for gara in cambi:
            tochange = dict()  # index, newcat
            for atleta, new_cat in cambi[gara].get('cambio_categoria', {}).items():
                if not data.query('garaname == @gara and classname == @new_cat').empty:
                    print("ERROR")
                index = data.query('garaname == @gara and name == @atleta').index[0]
                tochange[index] = new_cat
            data.loc[tochange.keys(), 'classname'] = list(tochange.values())
    return data


def classificato(data, atleta, config):
    global status
    if 'PROVVIS' in status:
        return True
    else:
        return len(data.query('name==@atleta and points > 0')) >= config['min_gare_per_classificato']


def calcola_recuperi(data, config):
    formula = config.get('recupero_formula', ('mean_best', 2))
    gare = config['recuperi']
    if not gare:
        return dict()
    recuperi = dict()
    for gara in gare:
        for atl in gare.get(gara, []):
            atl_data = data.query('name == @atl and points > 0')
            if not atl_data.empty and classificato(atl_data, atl, config):
                cat = atl_data['classname'].mode()[0]
                if formula[0] == 'mean_best':
                    recuperi[(gara, atl, cat)] = np.mean(sorted(np.nan_to_num(atl_data['points']), reverse=True)[0:formula[1]])
            else:
                log.warning("Recupero a '%s' per %s non assegnato" % (atl, gara))
    return recuperi


def assegna_recuperi(tabellone, recuperi):
    for (gara, atl, cat), value in recuperi.items():
        tabellone.at[(cat, atl), gara] = value
    return tabellone


def lst(df):
    points_per_rank = [20, 17, 14, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2] + [1]*100
    rank = df.query('status=="OK"') \
        .groupby(['garaname','classname'])['time'] \
        .rank(method='min', ascending=True) \
        .astype(int)
    out = rank.apply(lambda x: points_per_rank[x-1]).astype(int)
    return out


def compute_ranking(data, config):
    categorie = config['categorie']
    gare = config['gare']
    data = data.query("classname in @categorie and person_id==person_id").copy()

    # CAMBIO CATEGORIE PER ACCORPAMENTI
    data = cambio_categoria(data, config['cambio_categoria'])

    # CALCOLO PUNTEGGI GARE
    if config['formula_punteggio'] == 'classica':
        pv = config['punti_vincitore']
        winner_time = data.query('status=="OK"').groupby(['garaname', 'classname'])['time'].min()
        point_func = lambda x: (pv[x['classname']] if x['classname'] in pv else pv['default']) * \
                               ((winner_time[x['garaname']][x['classname']] / x['time']) ** 2) if x['status'] == "OK" else 0
        data['points'] = data.apply(point_func, axis=1)
    elif config['formula_punteggio'] == 'lst':
        data['points'] = lst(data)

    # Assegna 0 punti ai PM, PE, ecc.
    # data['points'] = np.where(data.status != 'OK' and data.status != 'DidNotStart', 0, data.points)
    data.loc[(data.status != 'OK') & (data.status != 'DidNotStart'), 'points'] = 0

    # CALCOLO TABELLONE CLASSIFICA TROFEO
    table = data.pivot_table(values='points',
                             index=['classname', 'name'],
                             columns=['garaname']) \
        .reindex(config['gare'].keys(), axis=1)

    class_func = lambda x: 'CL' if x.count() >= config['min_gare_per_classificato'] or 'PROVVIS' in status else 'NC'
    table['Status'] = table.apply(class_func, axis=1)

    # RECUPERI PUNTEGGI
    recuperi = dict()
    recuperi = calcola_recuperi(data, config)
    if status == 'DEFINITIVO':
        table = assegna_recuperi(table, recuperi)

    # CALCOLO PUNTEGGIO TOTALE CON SCARTI
    nscarti = config['n_scarti']
    table['Totale'] = table.drop('Status', axis=1) \
        .apply(lambda x: sum(sorted(np.nan_to_num(x), reverse=True)[:len(x)-nscarti]),
                                 axis=1).round(2)
    # table['Posizione'] = table.query('Status == "CL"').sort_values('Totale', ascending=False).groupby('classname').cumcount() + 1
    # table['Posizione'] = table['Posizione'].fillna('NC')
    table['Posizione'] = table.query('Status == "CL"') \
        .groupby('classname')['Totale'] \
        .rank(method='min', ascending=False) \
        .astype(int)

    # FORMAT OUTPUT
    tableout = table.copy()
    # tableout[list(gare.values())] = tableout[list(gare.values())].round(2).astype('str').replace('nan', '')
    if config['formula_punteggio'] == 'lst':
        pformat = "{0:.0f}"
    else:
        pformat = "{0:.2f}"
    tableout[list(gare.keys()) + ['Totale']] = tableout[list(gare.keys()) + ['Totale']] \
        .applymap(pformat.format) \
        .replace('nan', '')

    for (gara, atl, cat) in recuperi.keys():
        print(gara, atl, cat)
        tableout.loc[(cat, atl), gara] = '*' + str(tableout.loc[(cat, atl), gara])

    societa = data[['name', 'organisation_name']].drop_duplicates()

    tableout = tableout.reset_index().join(societa.set_index('name'), on='name')
    tableout = tableout.sort_values(['classname', 'Status', 'Posizione'], ascending=[True, True, True])
    tableout = tableout.rename(columns={'organisation_name': 'Società', 'classname': 'Categoria', 'name': 'Nome'})
    columns = ["Categoria", "Posizione", "Nome", "Società", "Totale"] + list(gare.keys())
    tableout = tableout.reindex(columns, axis=1)
    rename = {k: k+" | " + v[1][:-5] for k, v in gare.items()}
    tableout = tableout.rename(columns=rename)

    return tableout


def export_pdf(rank, config, filename=None):
    # Inspired by http://pbpython.com/pdf-reports.html
    filename = filename or basename(CONFIG_FILE).split('.')[0] + '.pdf'
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template("template.html")
    # class_rankings = [x.to_html() for x in rank.groupby("Categoria")]
    template_vars = {"title": config['nome_competizione'],
                     "rank": rank,
                     "now": datetime.now().strftime("%d/%m/%Y")}
    html_out = template.render(template_vars)
    HTML(string=html_out,
         base_url='.') \
        .write_pdf("out/" + filename)
    with open("out/prova.html", 'w') as f:
        print(html_out, file=f)


def main(config):
    global status
    assert config['source'] == 'fiso.it', "Unknown source"

    # Download results
    for id_gara, date in config['gare'].values():
        if parser.parse(date) < datetime.now():
            download_xml(id_gara)
        else:
            status = 'PROVVISORIO'

    print(status)

    # Compute rankings
    df = make_dataframe(config)
    df.to_csv('out/prova.csv', index=False)
    ranking = compute_ranking(df, config)

    # Publishing
    # ranking.to_csv('prova2.csv', float_format='%.02f', index=False)
    ranking.to_csv('out/prova2.csv', index=False)
    export_pdf(ranking, config)


if __name__ == '__main__':
    config = yaml.load(open(CONFIG_FILE))
    main(config)