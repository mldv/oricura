import yaml
import logging as log

from .loader import Loader
from .ranker import Ranker
from .exporter import Exporter

log.getLogger().setLevel(log.INFO)


def main(config_path: str, out='out.pdf'):

    log.info(config_path)
    config = yaml.load(open(config_path))

    _loader = Loader(config)
    df_race_res = _loader.load()

    _ranker = Ranker(config)
    ranking = _ranker.compute_ranking(df_race_res)

    _exporter = Exporter(config, ranking)
    if out.endswith('pdf'):
        _exporter.to_pdf(out)
        print("PDF file successfully generated.")
    elif out.endswith('html'):
        _exporter.to_html(out)
        print("HTML file successfully generated.")
