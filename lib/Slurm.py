header = (
        "#!/bin/bash\n"
        "\n"
        "#SBATCH --job-name=XChemExplorer_{subprocess}\n"
        "#SBATCH --ntasks=1\n"
        "#SBATCH --nodes=1\n"
        "#SBATCH --mem-per-cpu=32G\n"
        "#SBATCH --time=02:00:00\n" # Time limit hrs:min:sec
        "#SBATCH --output=%x_%j_slurm.out\n" # Standard output and error log
        )
