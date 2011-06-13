def product(first, *rest):
    if not rest: 
        for element in first: 
            yield element
    else:
        for element in first:
            for item in product(*rest):
                yield element + item

def lst_concatenate(lst):
    if isinstance(lst, str):
        return [lst]
    res = []
    for item in map(lst_extend, lst): 
        res.extend(item)
    return res

def lst_extend(lst):
    return list(product(*map(lst_concatenate, lst)))

def expand(text):
    """
    Perform bash-like produce brace expansion. e.g. a{b,c} => ["ab", "ac"]
    """
    from pyparsing import (Suppress, Optional, CharsNotIn, Forward, Group,
                           ZeroOrMore, delimitedList)

    lbrack, rbrack = map(Suppress, "{}")

    optAnything = Optional(CharsNotIn("{},"))

    braceExpr = Forward()

    listItem = optAnything ^ Group(braceExpr)

    bracketedList = Group(lbrack + delimitedList(listItem) + rbrack)
    braceExpr << optAnything + ZeroOrMore(bracketedList + optAnything)

    result = braceExpr.parseString(text).asList()
    
    return list(lst_extend(result))
    
def get_expand(f, text):
    return [f.Get(x) for x in expand(text)]
