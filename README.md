# oricura: Orienteering Custom Rankings
Tools for generating customized rankings from orienteering race results in IOF xml format.
In Python3.

**WARNING: in development**


## Installation

Make sure to have the dependencies specified in `requirements.txt`.


## Basic usage

Example: 
```bash
python oricura config/trofeo_lombardia_2019.yaml --out classifica.pdf
```

Supported output format: PDF, CSV, HTML.


### Configuration and customization

See `config/trofeo_lombardia_2019.yaml` for an example of configuration.

Additional formulas for computing the ranking can be added to `oricura/formulas.py`.

See `config/template.yaml` for an example of template for HTML and PDF output.


## How it works

There are two pandas dataframe involved to store data: `races_result` and `ranking`.

`races_result` stores races result.
Each row corresponds to a race result of an athlete (primary key: (race, athlete)).
It is produced by method `Loader.load` from IOF-XML files.

`ranking` stores the final ranking of the tournament/league/cup.
Each row corresponds to an athlete and contains info about points gained by the athlete in the races (primary key: (class, athlete)).
It is produced by method `Ranker.compute_ranking` from `races_result` and the rules defined in the config file.

