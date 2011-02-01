from logging import getLogger, basicConfig; log = getLogger("quick_repeat")
from sys import argv

def main():
    basicConfig()
    
    to_run = argv[1]
    argv[:] = [argv[0]] + argv[2:]
        
    while True:
        try:
            modparts = to_run.split(":")
            if len(modparts) == 2:
                modname, funcname = modparts
            else:
                (modname,) = modparts
                funcname = "main"
                
            print "Importing", modname
            mod = reload(__import__(modname, fromlist=[funcname]))
            getattr(mod, funcname)()
            
        except KeyboardInterrupt, SystemExit:
            raise
        except Exception:
            log.exception("Caught exception")
        
        try:
            raw_input("Press enter to rerun\n")
        except EOFError:
            break
