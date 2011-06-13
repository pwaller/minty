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

yaml.add_representer(unicode, 
    lambda dumper, value: dumper.represent_scalar(u'tag:yaml.org,2002:str', value))

class Dataset(yaml.YAMLObject):
    yaml_tag = u'!Atlas.Dataset'
    
    def __init__(self, contents):
        def c(value):
            if value.isdigit():
                return int(value)
            return value
    
        self.contents = dict((k.lower(), c(v)) for k, v in contents.iteritems())
        
    def __getattr__(self, what):
        if what == "contents":
            return {}
        if what not in self.contents:
            raise AttributeError(what)
        return self.contents[what]
    
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
