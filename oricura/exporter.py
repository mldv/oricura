from datetime import datetime

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML


class Exporter:
    def __init__(self, config, ranking):
        self.config = config
        self.ranking = ranking
        self.html_out = None

    @staticmethod
    def create_html(config, ranking):
        # Inspired by http://pbpython.com/pdf-reports.html
        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template("config/template.html")
        # class_rankings = [x.to_html() for x in rank.groupby("Categoria")]
        template_vars = {"title": config['nome_competizione'],
                         "rank": ranking,
                         "now": datetime.now().strftime("%d/%m/%Y")}
        return template.render(template_vars)

    def to_pdf(self, filename=None):
        filename = filename or 'out.pdf'

        if not self.html_out:
            self.html_out = Exporter.create_html(self.config, self.ranking)

        HTML(string=self.html_out,
             base_url='.') \
            .write_pdf(filename)

        return self

    def to_html(self, filename=None):
        filename = filename or 'out.html'

        if not self.html_out:
            self.html_out = Exporter.create_html(self.config, self.ranking)

        with open(filename, 'w') as f:
            print(self.html_out, file=f)

        return self

    def to_csv(self, filename=None):
        filename = filename or 'out.csv'
        self.ranking.to_csv(filename, index=False)
        return self