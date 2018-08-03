#----Patterns-----#
# This file is here to compile the regex patterns for use in regexMethodSignatures
# this is for the optimization of the re.search() function

import re

# pattern for regexClassName
regex_class_name = re.compile(r'([^\s]+)\:\:[^\s]+\(')

# patterns for regexReturnTypes
# don't have more descriptive names than this, I could not tell you what each of these are for but I know the function works lol
regex_return_types1 = re.compile(r'^(.+?\()')
regex_return_types2 = re.compile(r'(.+)\s[^\s]+\(')
regex_return_types3 = re.compile( r'[^\s]+,\s*.+?$' )
regex_return_types4 = re.compile(r'(.+)\s[^\s]+\(' )
regex_return_types5 =  re.compile( r'[^\s]+$' )

# patterns for regexParams
regex_params = re.compile(r'\(.+\)' )

# pattern for regexMethodName
regex_method_name = re.compile(r'([^\s\:]+)\(' )
