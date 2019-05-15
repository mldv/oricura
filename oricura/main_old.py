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