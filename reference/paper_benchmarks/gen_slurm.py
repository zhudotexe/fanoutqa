SETTINGS = (
    "openbook",
    "closedbook",
    "wiki_provided",
)
MODELS = {
    "gpt-4": "small",
    "gpt-4-turbo": "small",
    "gpt-3.5-turbo": "small",
    "llama-chat": "large",
    "mistral-chat": "med",
    "mixtral": "large",
    # "longllama": "large",
    "claude": "small",
}
TEMPLATE = """\
#!/bin/bash
#
#SBATCH --partition=p_nlp
#SBATCH --job-name=foqa-{model}{fn_extra}-{setting}
#SBATCH --output=/nlp/data/andrz/logs/%j.%x.log
#SBATCH --error=/nlp/data/andrz/logs/%j.%x.log
#SBATCH --time=7-0
#SBATCH -c {cpus}
#SBATCH --mem={mem}
#SBATCH --gpus={gpus}
{gpuconstraint}
export WIKI_CACHE_DIR=/nlp/data/andrz/fanoutqa-bench/.wikicache
srun python run_{setting}.py -m {model}{extra}
"""


def write_slurm_file(setting, model, extra="", fn_extra=""):
    size = MODELS[model]
    if size == "small":
        cpus = 4
        mem = "32G"
        gpus = 0
        gpuconstraint = ""
    elif size == "med":
        cpus = 4
        mem = "64G"
        gpus = 1
        gpuconstraint = "#SBATCH --constraint=48GBgpu"
    else:
        cpus = 16
        mem = "128G"
        gpus = 3
        gpuconstraint = "#SBATCH --constraint=48GBgpu"

    content = TEMPLATE.format(
        setting=setting,
        model=model,
        cpus=cpus,
        mem=mem,
        gpus=gpus,
        gpuconstraint=gpuconstraint,
        extra=extra,
        fn_extra=fn_extra,
    )
    with open(f"slurm/{model}{fn_extra}-{setting}.sh", "w") as f:
        f.write(content)


def main():
    for s in SETTINGS:
        for m in MODELS:
            write_slurm_file(s, m)

    for m in MODELS:
        write_slurm_file("openbook", m, extra=" --ctx-size 4096", fn_extra="-short")
        write_slurm_file("wiki_provided", m, extra=" --ctx-size 4096", fn_extra="-short")


if __name__ == "__main__":
    main()
