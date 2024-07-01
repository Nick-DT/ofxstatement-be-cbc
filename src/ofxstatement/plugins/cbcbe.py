from ofxstatement.plugin import Plugin
from ofxstatement.parser import CsvStatementParser
from ofxstatement.statement import StatementLine
from ofxstatement.exceptions import ParseError
import csv

LINELENGTH = 18
HEADER_START = "Numéro de compte"


class CbcBePlugin(Plugin):
    """Belgian CBC Bank plugin for ofxstatement
    """

    def get_parser(self, filename):
        f = open(filename, 'r')
        parser = CbcBeParser(f)
        return parser


class CbcBeParser(CsvStatementParser):
    date_format = "%d/%m/%Y"

    header =["Numéro de compte","Nom de la rubrique","Nom","Devise","Numéro de l'extrait","Date",
             "Description","Valeur","Montant","Solde","crédit","débit",
             "numéro de compte contrepartie","BIC contrepartie","Nom contrepartie",
             "Adresse contrepartie","communication structurée","Communication libre"]

    col_index = dict(zip(header, range(0, 18)))

    mappings = {
        'memo'      : col_index['Description'],
        'date'      : col_index['Date'],
        'amount'    : col_index['Montant'],
        'check_no'  : col_index["Numéro de l'extrait"],
        'refnum'    : col_index["Numéro de l'extrait"],
        'id'     : col_index["Numéro de l'extrait"]
    }

    line_nr = 0

    def parse_float(self, value):
        """Return a float from a string with ',' as decimal mark.
        """
        return float(value.replace(',', '.'))

    def split_records(self):
        """Return iterable object consisting of a line per transaction
        """
        return csv.reader(self.fin, delimiter=';')

    def parse_record(self, line):
        """Parse given transaction line and return StatementLine object
        """
        self.line_nr += 1
        if line[0] == HEADER_START:
            return None
        elif len(line) != LINELENGTH:
            raise ParseError(self.line_nr,
                             'Wrong number of fields in line! ' +
                             'Found ' + str(len(line)) + ' fields ' +
                             'but should be ' + str(LINELENGTH) + '!')

        # Check the account id. Each line should be for the same account!
        if self.statement.account_id:
            if line[0] != self.statement.account_id:
                raise ParseError(self.line_nr,
                                 'AccountID does not match on all lines! ' +
                                 'Line has ' + line[0] + ' but file ' +
                                 'started with ' + self.statement.account_id)
        else:
            self.statement.account_id = line[0]

        # Check the currency. Each line should be for the same currency!
        if self.statement.currency:
            if line[3] != self.statement.currency:
                raise ParseError(self.line_nr,
                                 'Currency does not match on all lines! ' +
                                 'Line has ' + line[3] + ' but file ' +
                                 'started with ' + self.statement.currency)
        else:
            self.statement.currency = line[3]

        stmt_ln = super(CbcBeParser, self).parse_record(line)

        # Now if available add the account nb, and if no payee name use account nb instead
        stmt_ln.payee = line[self.col_index['numéro de compte contrepartie']].strip() # Payee defaults to account nb
        if line[self.col_index['Nom contrepartie']] :
            if (not line[self.col_index['numéro de compte contrepartie']]) : 
                stmt_ln.payee = line[self.col_index['Nom contrepartie']].strip() # but if empty and name isn't, take the name
            else : 
                stmt_ln.payee = line[self.col_index['Nom contrepartie']].strip() +" - "+ stmt_ln.payee

        stmt_ln.trntype = 'DEBIT' if stmt_ln.amount < 0 else 'CREDIT'

        # Additional ID for software relying on it
        #stmt_ln.id = line[self.col_index["Numéro de l'extrait"]]
        stmt_ln.id = stmt_ln.id.strip()
        stmt_ln.check_no= stmt_ln.check_no.strip()
        stmt_ln.refnum  = stmt_ln.refnum.strip()

        return stmt_ln
