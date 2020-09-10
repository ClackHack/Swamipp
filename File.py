import Swamipp as Swami
import os,datetime
import _thread, sys
import argparse
parser = argparse.ArgumentParser(description="Swami++")
parser.add_argument("file",nargs="?",type=str,help="file to be executed",default="")
args=parser.parse_args()
if args.file:
  try:
    code=open(args.file,"r").read()
    y=datetime.datetime.now()
    result,error=Swami.run(args.file,code)
    x=datetime.datetime.now()
    if error:
        print(error.toString(),sep="\n")
    else:
        print(f"\nExecuted with zero errors in {(x-y).total_seconds()} seconds")
  except KeyboardInterrupt:
    sys.exit()
  except Exception as e:
    print("Could not find file, or fatal error...",e)
  else:
      input("Press 'enter' to exit...")
  sys.exit()
