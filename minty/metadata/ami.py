"""
amiCommand BrowseSQLQuery -sql="SELECT dataset.* FROM dataset WHERE dataset.logicalDatasetName LIKE 'data11_7TeV.00%.physics_Egamma.merge.NTUP_PHOTON.%_p555%' ORDER BY dataset.RUNNUMBER" -nbElements="1000" -output=xml
"""
#-processingStep="real_data" -project="data11_001" 

#ListDataset predicate="logicalDatasetName LIKE 'data11_7TeV.00%.physics_Egamma.merge.NTUP_PHOTON.%_p555%'" project=data11_001 processingStep=real_data select=logicalDatasetName,nfiles,totalevents

from pyAMI.pyAMI import AMI
import pyAMI
amiclient = AMI(False)

class Dataset(object):
    def __repr__(self):
        return ("<Dataset run={s.period}.{s.run} status=({s.status}, {s.amistatus}) "
                "events={s.events} name={s.name}>").format(s=self)

def make_dataset(x):
    d = Dataset()
    for key, value in x.iteritems():
        if value.isdigit():
            value = int(value)
        setattr(d, key.lower(), value)
    d.run = d.runnumber if hasattr("d", "runnumber") else d.datasetnumber
    d.period = d.period if hasattr("d", "period") else "MC"
    d.status = d.prodsysstatus
    d.name = d.logicaldatasetname
    d.files = d.nfiles
    d.events = d.totalevents
    d.good = d.status == "EVENTS_AVAILABLE" and d.amistatus == "VALID"
    return d    

def query_datasets(pattern):
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

    result = amiclient.execute(args).getDict()
    #from IPython.Shell import IPShellEmbed
    #ip = IPShellEmbed(['-pdb'])
    #ip()
    datasets = [make_dataset(d) for d in result["dataset"].values()]
    
    return sorted((d for d in datasets if d.good), key=lambda d: d.run)

#from pprint import pprint
#pprint(result)


#ip()

#query_datasets("data11_7TeV.00%.physics_Egamma.merge.NTUP_PHOTON.%_p555%'")
