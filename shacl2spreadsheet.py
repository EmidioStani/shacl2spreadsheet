from pathlib import Path
from typing import Optional
from unicodedata import decimal

import xlsxwriter
import yaml
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, SKOS
from xlsxwriter.worksheet import (Worksheet, cell_number_tuple,
                                  cell_string_tuple)


def get_config(file):
    my_path = Path(__file__).resolve()  # resolve to get rid of any symlinks
    config_path = my_path.parent / file
    with config_path.open() as config_file:
        config = yaml.load(config_file, Loader=yaml.FullLoader)
    return config

def get_column_width(worksheet: Worksheet, column: int) -> Optional[int]:
    """Get the max column width in a `Worksheet` column."""
    strings = getattr(worksheet, '_ts_all_strings', None)
    if strings is None:
        strings = worksheet._ts_all_strings = sorted(
            worksheet.str_table.string_table,
            key=worksheet.str_table.string_table.__getitem__)
    lengths = set()
    for row_id, colums_dict in worksheet.table.items():  # type: int, dict
        data = colums_dict.get(column)
        if not data:
            continue
        if type(data) is cell_string_tuple:
            iter_length = len(strings[data.string])
            if not iter_length:
                continue
            lengths.add(iter_length)
            continue
        if type(data) is cell_number_tuple:
            iter_length = len(str(data.number))
            if not iter_length:
                continue
            lengths.add(iter_length)
    if not lengths:
        return None
    return max(lengths)

def set_column_autowidth(worksheet: Worksheet, column: int, coeff: float):
    """
    Set the width automatically on a column in the `Worksheet`.
    !!! Make sure you run this function AFTER having all cells filled in
    the worksheet!
    """
    maxwidth = get_column_width(worksheet=worksheet, column=column)
    if maxwidth is None:
        return
    worksheet.set_column(first_col=column, last_col=column, width=maxwidth*coeff)

config = get_config("config.yaml")

g = Graph()
g.parse(config['input']['file'] , format=config['input']['format'])

workbook = xlsxwriter.Workbook(config['output']['file'])

ns1 = Namespace(config["namespaces"]["shacl"])
for s, p, o in g.triples((None, RDF.type, ns1.NodeShape)):
    start = config['input']['shapestart']
    end = config['input']['shapeend']
    worksheet_name = ((s.split(start))[1].split(end)[0]).replace(":","_")
    worksheet = workbook.add_worksheet(worksheet_name)
    
    for prefix, namespace in config["namespaces"].items():
        g.bind(prefix, Namespace(namespace))

    cell_format = workbook.add_format()
    cell_format.set_bold()

    worksheet.write('A1', config['output']['classuri'], cell_format)
    for ns, tc, cl in g.triples((s, ns1.targetClass, None)):
        worksheet.write('B1', str(cl))

    num_namespaces = len(config["namespaces"])
    for index, i in enumerate(config["namespaces"].items()):
        worksheet.write(index+1, 0, config['output']['prefix'] , cell_format)
        worksheet.write(index+1, 1, i[0])
        worksheet.write(index+1, 2, i[1])

    # worksheet.write(num_namespaces + 1, 0, config['output']['rdftype'], cell_format)
    # worksheet.write(num_namespaces + 1, 1, config['output']['rdfclass'])

    cell_format2 = workbook.add_format()
    cell_format2.set_bold()
    cell_format2.set_bg_color(config['output']['line']['bgcolor'])

    propertiesrow = num_namespaces + 2
    worksheet.write(propertiesrow, 0, config['output']['line']['URI'], cell_format2)
    worksheet.write(propertiesrow, 1, config['output']['line']['type'], cell_format2)
    mylist = []
    mylist2 = []
    for a, b, c in g.triples((s, ns1.property, None)):
        for d, e, f in g.triples((c, ns1.path, None)):
            # print(f)
            property = URIRef(f)
            mylist.append(property.n3(g.namespace_manager))
        
        for d, e, f in g.triples((c, None, None)):
            if e == ns1.datatype:
                mylist2.append(f)
            if e == ns1['class']:
                mylist2.append("uri")
    print(mylist2)
    mylist3 = []
    for index, i in enumerate(mylist):
        if (mylist2[index] == URIRef(config['output']['line']['datatypes']['langString']['namespace'])):
            element = i + config['output']['line']['datatypes']['langString']['suffix']
            mylist3.append(element)
        else:
            mylist3.append(i)
    worksheet.write_row(propertiesrow, 2, mylist3, cell_format2)
    num_columns = 3 + len(mylist)
    for i in range(num_columns):
        set_column_autowidth(worksheet, i, 1.15)

workbook.close()
