import argparse
import json
from .ingest import ingest_csv

parser = argparse.ArgumentParser(description='Ingest explicit canonical observations with provenance')
parser.add_argument('csv')
parser.add_argument('--metadata',required=True,help='Metadata JSON path')
parser.add_argument('--data-dir',default='data')
parser.add_argument('--chunk-size',type=int,default=50000)
args = parser.parse_args()
print(json.dumps(ingest_csv(args.csv,json.load(open(args.metadata)),args.data_dir,args.chunk_size),indent=2))
