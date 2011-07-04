"""
amiCommand BrowseSQLQuery -sql="SELECT dataset.* FROM dataset WHERE dataset.logicalDatasetName LIKE 'data11_7TeV.00%.physics_Egamma.merge.NTUP_PHOTON.%_p555%' ORDER BY dataset.RUNNUMBER" -nbElements="1000" -output=xml
"""
#-processingStep="real_data" -project="data11_001" 

#ListDataset predicate="logicalDatasetName LIKE 'data11_7TeV.00%.physics_Egamma.merge.NTUP_PHOTON.%_p555%'" project=data11_001 processingStep=real_data select=logicalDatasetName,nfiles,totalevents

import yaml

def get_amiclient():
    # Hack to prevent Ft module from overriding showwarnings with something broken
    # (imported by pyAMI)
    from warnings import showwarning
    showwarning.__module__ = "Ft"

    from pyAMI.pyAMI import AMI
    import pyAMI
    amiclient = AMI(False)
    return amiclient

def try_float(value):
    try:
        return float(value)
    except ValueError:
        return value

def try_conversion(value):
    if value.isdigit():
        return int(value)
    return try_float(value)    

yaml.add_representer(unicode, 
    lambda dumper, value: dumper.represent_scalar(u'tag:yaml.org,2002:str', value))

class ContentsWrapper(object):
    """
    A class which gives attribute lookup into a dictionary, and can be built 
    from a dictionary. Values equal to the empty string are ignored.
    """
    def __init__(self, contents):
        self.contents = dict((k.lower(), try_conversion(v)) 
                             for k, v in contents.iteritems() if v != "")
    
    def clean(self):
        self.contents = dict((key, value) 
                             for key, value in self.contents.iteritems()
                             if value)
        return self
    
    def __getattr__(self, what):
        if what == "contents":
            # Contents hasn't been set yet. Return empty set.
            return {}
        if what not in self.contents:
            raise AttributeError(what)
        return self.contents[what]
    

class MonteCarloInfo(ContentsWrapper, yaml.YAMLObject):
    yaml_tag = u'!Atlas.MonteCarloInfo'

    @classmethod
    def from_ds(cls, ds):
        import PyUtils.AmiLib as A
        c = A.Client()
        x = c.exec_cmd("GetDatasetInfo", logicalDatasetName=ds.evgen_name)
        return cls(x.getDict().values()[0].values()[0])

class Dataset(ContentsWrapper, yaml.YAMLObject):
    yaml_tag = u'!Atlas.Dataset'
    
    @property
    def evgen_name(self):
        left, merge, right = self.name.partition(".merge.")
        return "{0}.evgen.EVNT.{1}".format(left, self.version.split("_")[0])
    
    @property
    def name(self):
        return self.logicaldatasetname
    
    @property
    def status(self): 
        return self.prodsysstatus
        
    @property
    def good(self): 
        return self.status == "EVENTS_AVAILABLE" and self.amistatus == "VALID"
    
    @property
    def events(self):
        return self.totalevents
    
    @property
    def run(self):
        return self.runnumber if "runnumber" in self.contents else self.datasetnumber
    
    @property
    def mc_info(self):
        if "mc_info" in self.contents:
            return self.contents["mc_info"]
        self.contents["mc_info"] = MonteCarloInfo.from_ds(self)
    
    @property
    def period(self):
        if self.projectname.startswith("mc"):
            return "MC"
        if self.contents.get("period", None):
            return self.contents["period"]
        return "UNK"
    
    def __repr__(self):
        return ("<Dataset run={s.period}.{s.run} status=({s.status}, {s.amistatus}) "
                "events={s.events} name={s.name}>").format(s=self)

def make_dataset(x):
    d = Dataset(x)
    if not d.good:
        return None
    return d    

def query_datasets(pattern):
    pattern = pattern.replace("*", "%").rstrip("/")
    firstpart = pattern.split("_")[0]
    processing_step = "real_data" if "data" in firstpart else "production"
    if "data" in firstpart or "mc11" in firstpart:
        project = "{0}_001".format(firstpart)
    elif "mc" in firstpart:
        project = firstpart
    else:
        raise RuntimeError("I haven't considered this..")
        
    args = [
        "ListDataset",
        "predicate=logicalDatasetName LIKE '%s'" % pattern,
        "project={0}".format(project),
        "processingStep={0}".format(processing_step),
    ]

    result = get_amiclient().execute(args).getDict()
    #from IPython.Shell import IPShellEmbed
    #ip = IPShellEmbed(['-pdb'])
    #ip()
    datasets = [make_dataset(d) for d in result["dataset"].values()]
    
    return sorted((d for d in datasets if d and d.good), key=lambda d: d.run)

#from pprint import pprint
#pprint(result)


#ip()

#query_datasets("data11_7TeV.00%.physics_Egamma.merge.NTUP_PHOTON.%_p555%'")
