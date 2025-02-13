import re
import warnings
from .data import VCFDataHolder


# function for working with VCF files
def ploidy_from_vcf(path):
    """
    Calculate ploidy from .vcf file

    This function was written by Artyom Ershov as part of internship test task.
    Was taken from repository: https://github.com/iam28th/intership_test_task
    """
    # chrom name whose count of copies differs from ploidity
    bad_chroms = {'Y', 'X', 'M', 'chrX', 'chrY', 'chrM'}

    with open(path, 'r') as f:
        for line in f:
            # skip comments and heading
            if line.startswith('#'):
                continue

            # skip bad chroms
            fields = line.split('\t')
            chrom = fields[0]
            if chrom in bad_chroms:
                continue

            # .vcf contains 8 fixed columns + FORMAT + individual columns
            # i.e. first of individual columns is the 10th

            # find genotype field index
            index = fields[8].split(':').index('GT')
            # we want to divide by either | or /
            ploidy = len(re.split(r"\||/", fields[9].split(':')[index]))
            return ploidy


def read_popinfo(popinfo_file):
    """
    Returns dictionary {sample_name: pop_name} from popmap file and list of
    presented populations.
    """
    populations = []
    sample2pop = {}
    with open(popinfo_file) as fl:
        for line in fl:
            sample, pop = line.strip().split()
            if sample in sample2pop and pop != sample2pop[sample]:
                raise ValueError(f"Sample {sample} is presented in popmap "
                                 f"{popinfo_file} at least twice "
                                 "corresponding to different populations.")
            sample2pop[sample] = pop
            if pop not in populations:
                populations.append(pop)
    return sample2pop, populations


def get_list_of_names_from_vcf(vcf_file):
    """
    Returns list of sample names from vcf file.
    """
    header_line = ""
    with open(vcf_file) as fl:
        for line in fl:
            # Skip metainformation
            if line.startswith("#"):
                if line.startswith("##"):
                    continue
                header_line = line
                continue

            # Read header
            assert len(header_line) != 0, ("There is no header information in"
                                           f" VCF file {vcf_file}")
            # samples starts from 9 element
            header_info = header_line.split()
            assert len(header_info) > 9, ("There is no samples in VCF file "
                                          f" {vcf_file}: {header_line}")
            return header_info[9:]


def get_defaults_from_vcf_format(vcf_file, popmap_file, verbose=False):
    """
    Returns population labels and projections from files.
    if verbose is True then warnings are printed.

    If full then all samples will be used, missed ones will be put under
    `Unknown` population.
    """
    # Read popmap and check samples from vcf
    # check samples in vcf
    vcf_samples = get_list_of_names_from_vcf(vcf_file=vcf_file)

    # check popmap
    sample2pop, all_populations = read_popinfo(popinfo_file=popmap_file)
    pop_is_pres = {pop: False for pop in all_populations}
    for sample in sample2pop:
        pop_is_pres[sample2pop[sample]] = True
    populations = [pop for pop in all_populations if pop_is_pres[pop]]

    # check our lists
    # samples that are in popmap but not in vcf
    missed_samples = [smpl for smpl in sample2pop if smpl not in vcf_samples]
    if len(missed_samples) > 0 and verbose:
        warnings.warn("The following samples are presented in popmap file but "
                      f"not in VCF file: {missed_samples}")
    missed_samples = [smpl for smpl in vcf_samples if smpl not in sample2pop]
    if len(missed_samples) > 0 and verbose:
        warnings.warn("The following samples are presented in VCF file but "
                      f"not in popmap file: {missed_samples}")
    # evaluate maximum projections for our data
    pop2num = {}
    for pop in populations:
        pop2num[pop] = len([_sample for _sample, _pop in sample2pop.items()
                            if _sample in vcf_samples and _pop == pop])
    full_projections = [2 * pop2num[pop] for pop in populations]
    return populations, full_projections


def check_population_labels_vcf(pop_labels, full_pop_labels):
    """
    Checks that current labels are subset of full labels.
    """
    corr_labels = [lab in full_pop_labels for lab in pop_labels]
    assert all(corr_labels), f"Some given labels are not presented in VCF "\
                             f"file.\nGot labels: {pop_labels}\n"\
                             f"Labels in VCF file: {full_pop_labels}"


def check_projections_vcf(projections, full_projections, pop_labels):
    """
    Checks that projections are less than full projections.
    """
    corr_proj = [proj1 <= proj2 for proj1, proj2 in zip(projections,
                                                        full_projections)]
    assert all(corr_proj), "Something wrong with given projections. They are "\
                           "greater than number of samples presented in VCF "\
                           "file.\nGiven pop. labels and projections: "\
                           f"{pop_labels}, {projections}\nPop.labels "\
                           "and projections from VCF file: "\
                           f"{pop_labels}, {full_projections}."


def check_and_return_projections_and_labels(data_holder, verbose=False):
    """
    Takes VCF data holder and checks that its info is okay for vcf and popmap.
    Returns valid projections and population labels (could be used for the
    same data holder).
    """
    assert isinstance(data_holder, VCFDataHolder)
    # get info from popmap and vcf
    full_populations, full_projections = get_defaults_from_vcf_format(
        vcf_file=data_holder.filename,
        popmap_file=data_holder.popmap_file,
        verbose=verbose
    )
    # get holder info
    holder_pop_labels = data_holder.population_labels
    holder_proj = data_holder.projections
    if holder_proj is not None:
        holder_proj = list(holder_proj)
    populations = full_populations
    # check for population labels
    if holder_pop_labels is not None:
        check_population_labels_vcf(
            pop_labels=holder_pop_labels,
            full_pop_labels=full_populations
        )
        populations = holder_pop_labels
    # check for projections
    pop2proj = dict(zip(full_populations, full_projections))
    projections = [pop2proj[pop] for pop in populations]
    if holder_proj is not None:
        if len(projections) != len(holder_proj):
            all_less = False
        else:
            all_less = all(
                [pr1 <= pr2 for pr1, pr2 in zip(holder_proj, projections)]
            )
        assert all_less, ("Data cannot be downsized. Sample size of VCF data "
                          f"for {populations} populations are {projections} "
                          f"and got projections {holder_proj}.")
        projections = holder_proj
    return projections, populations
