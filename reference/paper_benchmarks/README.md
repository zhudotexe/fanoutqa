# benchmarks

make sure to do `python -m spacy download en_core_web_sm`

closedbook: just the q and 0 shot prompt to output short text

openbook: like closedbook but you can search wikipedia wowza

wiki provided: chunk the known evidence 1024 characters at a time (preferring splitting at paragraph and sentence
boundaries), retrieve as many passages fit into context window as possible, use bm25

run:

```shell
WIKI_CACHE_DIR=/nlp/data/andrz/fanoutqa-bench/.wikicache python run_openbook.py -m mistral-chat -n 3
for i in slurm/*; do sbatch $i; done
```

# eval

install:

```shell
wget https://storage.googleapis.com/bleurt-oss-21/BLEURT-20.zip
unzip BLEURT-20.zip
rm BLEURT-20.zip
python -m spacy download en_core_web_sm
```