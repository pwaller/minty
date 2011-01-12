#! /usr/bin/env python

from pyAMI import pyAMI

from IPython.Shell import IPShellEmbed as E; sh = E(["-pdb"])

def fields_to_dict(fields):
    return dict((f.attributes["name"].value, getattr(f.firstChild, "data", None))
                for f in fields)

def ami_result_to_dict(ami_result):
    return fields_to_dict(ami_result.getAMIdom().getElementsByTagName("field"))

def get_ds_info(ds_name):
    argument=[]
    argument.append("GetDatasetInfo")
    argument.append("logicalDatasetName=%s" % ds_name)
    amiclient = pyAMI.AMI()
    result = amiclient.execute(argument)
    r = ami_result_to_dict(result)
    assert r["crossSection_unit"] == "nano barn"
    return float(r["crossSection_mean"]), int(r["totalEvents"]), float(r["GenFiltEff_mean"])

def datasets_from_id(ds_number):
    argument=[]
    argument.append("SearchQuery")
    argument.append("entity=dataset")
    argument.append("glite=SELECT logicalDatasetName WHERE "
                    "amiStatus='VALID' AND "
                    "datasetNumber=%i AND "
                    "logicalDatasetName like 'mc09_7TeV%%' AND "
                    "dataType='EVNT' AND "
                        "(prodsysStatus like 'EVENTS_AVAILABLE%%' OR "
                        "prodsysStatus like 'DONE%%')" % ds_number)
    argument.append("project=Atlas_Production")
    argument.append("processingStep=Atlas_Production")
    #argument.append("mode=defaultField")
    amiclient = pyAMI.AMI()
    result = amiclient.execute(argument)
    rs = [l.split()[0] for l in result.output().split("logicalDatasetName = ")][1:]
    return rs

def main():
    from sys import argv
    for ds_num in argv[1:]:
        dsid = int(ds_num.strip())
        dss = datasets_from_id(dsid)
        ds_infos = [get_ds_info(ds) for ds in dss]
        
        #print dsid
        for ds, ds_info in zip(dss, ds_infos)[:1]:
            xs, n, filteff = ds_info
            efflum = (n / filteff) / xs
            targlum = 40000 # 40/pb
            print "#", ds
            print "minty-scale %f %s %s" % (targlum / efflum, "PMC-%i.root" % dsid, "PMC-%i-scaled.root" % dsid)
            #print "", ds, targlum / efflum, efflum, ds_info

