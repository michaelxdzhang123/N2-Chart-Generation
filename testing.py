

import re
from regexMethodSignatures import regexReturnTypes
from data_collection import commentRemover
import sqlite3 as sql
from collect_globals import collectGlobals
import os

# os.remove('globals.db')
# collectGlobals('C:\\Users\\sspelsbe\\28d_html')
#
# # connection = sql.connect('globals.db')
# # crsr = connection.cursor()
# #
# # crsr.execute('SELECT * FROM globals WHERE var_name = ?', ('extEtherIndex',))
# # print(crsr.fetchall())

full_name = 'Meth#123'

full_name = full_name.split('::')
if len(full_name) == 1:
    class_name = 'Unknown'
    tmp = full_name[0].split('#')
    method_name = tmp[0]
    dict_link = tmp[1]
else:
    class_name = full_name[0].strip()
    tmp = full_name[len(full_name)-1].split('#')
    dict_link = tmp[1].strip()
    method_name = '::'.join(full_name[1:])
    method_name = method_name[:method_name.find('#')]


print(class_name, method_name, dict_link)
