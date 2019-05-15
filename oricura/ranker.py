import logging as log
import numpy as np

import oricura.formulas as formulas

config = dict()


class Ranker:

    def __init__(self, config, is_final=False):
        self.config = config
        self.is_final = is_final

    @staticmethod
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

    def classificato(self, data, atleta):
        if atleta is None:
            return False
        if self.is_final:
            return len(data.query('name==@atleta and points > 0')) >= self.config['min_gare_per_classificato']
        else:
            return True

    def calcola_recuperi(self, data, config):
        formula = config.get('recupero_formula', ('mean_best', 2))
        gare = config['recuperi']
        if not gare:
            return dict()
        recuperi = dict()
        for gara in gare:
            for atl in gare.get(gara, []):
                atl_data = data.query('name == @atl and points > 0')
                if not atl_data.empty and self.classificato(atl_data, atl):
                    cat = atl_data['classname'].mode()[0]
                    if formula[0] == 'mean_best':
                        recuperi[(gara, atl, cat)] = np.mean(sorted(np.nan_to_num(atl_data['points']), reverse=True)[0:formula[1]])
                else:
                    log.warning("Recupero a '%s' per %s non assegnato" % (atl, gara))
        return recuperi

    @staticmethod
    def assegna_recuperi(tabellone, recuperi):
        for (gara, atl, cat), value in recuperi.items():
            tabellone.at[(cat, atl), gara] = value
        return tabellone

    def compute_ranking(self, data):
        config = self.config
        categorie = config['categorie']
        assert categorie is not None
        gare = config['gare']
        data = data.query("classname in @categorie and person_id==person_id").copy()

        # CAMBIO CATEGORIE PER ACCORPAMENTI
        data = self.cambio_categoria(data, config['cambio_categoria'])

        # CALCOLO PUNTEGGI GARE
        formula_fun = getattr(formulas, self.config['formula_punteggio'])
        data['points'] = formula_fun(data)

        # Assegna 0 punti ai PM, PE, ecc.
        # data['points'] = np.where(data.status != 'OK' and data.status != 'DidNotStart', 0, data.points)
        data.loc[(data.status != 'OK') & (data.status != 'DidNotStart'), 'points'] = 0

        # CALCOLO TABELLONE CLASSIFICA TROFEO
        table = data.pivot_table(values='points',
                                 index=['classname', 'name'],
                                 columns=['garaname']) \
            .reindex(config['gare'].keys(), axis=1)

        def class_func(x):
            return 'CL' if x.count() >= config['min_gare_per_classificato'] or not self.is_final else 'NC'
        table['Status'] = table.apply(class_func, axis=1)

        # RECUPERI PUNTEGGI
        recuperi = self.calcola_recuperi(data, config)
        if self.is_final:
            table = self.assegna_recuperi(table, recuperi)

        # CALCOLO PUNTEGGIO TOTALE CON SCARTI
        nscarti = config['n_scarti']
        table['Totale'] = table.drop('Status', axis=1) \
            .apply(lambda x: sum(sorted(np.nan_to_num(x), reverse=True)[:len(x)-nscarti]),
                   axis=1).round(2)
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
