############################################################
# funcs to regex pieces of function from method signature
# either returns "" or matched string
import re
from regexMethodSignaturesPatterns import regex_class_name, regex_return_types1, regex_return_types2, regex_return_types3, regex_return_types4, regex_return_types5, regex_params, regex_method_name

def regexClassName( str ):
    """regexes class name from method signature"""
    class_name = regex_class_name.search(str)
    if class_name:
        return class_name.group(1)
    else:
        return ""

def regexReturnTypes( str ):
    """regex's return type from method signature"""
    return_type = regex_return_types1.search(str)
    if return_type:
        if return_type and " " not in return_type.group(): #no type specified
            return ""
        elif "," in return_type.group():
            tmp = regex_return_types2.search(return_type.group())
            tmp = regex_return_types3.search(tmp.group(1))
            return tmp.group()
        else:
            tmp2 = regex_return_types4.search(return_type.group())
            if tmp2 == None: #C style method header
                tmp2 = str.split()[0].strip()
                return tmp2
            else:
                tmp3 = regex_return_types5.search(tmp2.group(1) )
                try:
                    return tmp3.group()
                except:
                    return tmp2.group(1)
    else:
        return ""

def regexParams( str ):
    """regex's parameters from a method signature"""
    pr = regex_params.search(str)
    if pr:
        return pr.group()
    else:
        return ""

def regexMethodName( str ):
    """gets the method name from the method signature"""
    method_name = regex_method_name.search(str)
    if method_name:
        return method_name.group(1)

###################################
