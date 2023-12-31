from io import StringIO

import numpy as np
import pandas as pd
from Bio.Seq import Seq

# Define Function for calculating Modified Breslauer Melting Temperature (same algorithm as benchling)
# https://www.ncbi.nlm.nih.gov/pmc/articles/PMC323600/pdf/pnas00315-0187.pdf - original paper for algorithm and thermo quantities
# http://biotools.nubic.northwestern.edu/OligoCalc2.01.html - reference link for equation

# Dataframe of nearest nieghbor thermodynamic quantities. Used in the tm_calc() function
energies = pd.DataFrame.from_dict(
    {
        "Pair": [
            "AA",
            "AT",
            "AG",
            "AC",
            "TT",
            "TA",
            "TG",
            "TC",
            "GG",
            "GC",
            "GA",
            "GT",
            "CC",
            "CG",
            "CA",
            "CT",
        ],
        "H": [
            9.1,
            8.6,
            7.8,
            6.5,
            9.1,
            6,
            5.8,
            5.6,
            11,
            11.1,
            5.6,
            6.5,
            11,
            11.9,
            5.8,
            7.8,
        ],
        "S": [
            24,
            23.9,
            20.8,
            17.3,
            24,
            16.9,
            12.9,
            13.5,
            26.6,
            26.7,
            13.5,
            17.3,
            26.6,
            27.8,
            12.9,
            20.8,
        ],
        "G": [
            1.9,
            1.5,
            1.6,
            1.3,
            1.9,
            0.9,
            1.9,
            1.6,
            3.1,
            3.1,
            1.6,
            1.3,
            3.1,
            3.6,
            1.9,
            1.6,
        ],
    }
)

# set the pair column as the dataframe index
energies.set_index("Pair", inplace=True)


def tm_calc(seq):
    """
    Calculates the Modified Breslauer melting temperature for non-symetric
    oligonucleotides >8 bp, that contain at least one G or C
    """
    h_tot = 0
    s_tot = 0
    g_tot = 0

    for i in range(len(seq)):
        if i + 2 <= len(seq):
            pair = seq[i : i + 2]
            h = energies.loc[pair, "H"]
            s = energies.loc[pair, "S"]
            g = energies.loc[pair, "G"]

            h_tot += h
            s_tot += s
            g_tot += g

    numerator = h_tot - 3.4
    denominator = (s_tot / 1000) + 0.0019872 * np.log(1 / 0.25e-7)
    t = numerator / denominator + 16.6 * np.log10(0.05) - 272.15

    return t


def generate_primers(
    input_df, add_overhangs=False, upstream_overhang=None, downstream_overhang=None
):
    """
    Takes in a dataframe of gene sequences and returns the 'best' ranked fwd and rev primer to amplify each gene from all possible primers between 19-26 bp
    """
    # convert column headers to lowercase to avoid case sensitivity errors
    input_df.columns = map(str.lower, input_df.columns)

    # clean up sequences - remove spaces & new line characters, make uppercase
    input_df["sequence"] = (
        input_df["sequence"]
        .str.strip()
        .str.replace("\n", "")
        .str.replace("\r", "")
        .str.upper()
    )

    # Create dataframe to hold all primer options
    # for each amplicon list of possible forward & reverse primers b/w 19-26 bp
    options_tuples_list = []
    for index, row in input_df.iterrows():

        forward_options = []
        reverse_options = []

        forward_name = f"{row['amplicon name']} forward"
        reverse_name = f"{row['amplicon name']} reverse"

        option_group_idx_counter = 1

        for i in range(
            19, 27
        ):  # these numbers set the length range for potential primers you want to evaluate.

            forward_sequence = row["sequence"][:i]
            forward_options.append(
                (
                    row["amplicon name"],
                    forward_name,
                    "forward",
                    option_group_idx_counter,
                    forward_sequence,
                )
            )

            last_N = Seq(row["sequence"][-i:])
            # Use Biopython to get the reverse complement of gene end
            reverse_sequence = str(last_N.reverse_complement())
            reverse_options.append(
                (
                    row["amplicon name"],
                    reverse_name,
                    "reverse",
                    option_group_idx_counter,
                    reverse_sequence,
                )
            )

            option_group_idx_counter += 1

        options_tuples_list.extend(forward_options)
        options_tuples_list.extend(reverse_options)

    primer_options_df = pd.DataFrame(
        options_tuples_list,
        columns=[
            "amplicon_name",
            "primer_name",
            "direction",
            "option_group_index",
            "primer_sequence",
        ],
    )

    scored_primer_option_row_list = []
    for index, row in primer_options_df.iterrows():

        # check for GC clamp & add GC binary score
        if row["primer_sequence"][-1:] in ["G", "C"]:
            row["gc_clamp"] = 1
        else:
            row["gc_clamp"] = 0

        # add length
        row["length"] = len(row["primer_sequence"])

        # calculate & add GC%
        nG, nC = row["primer_sequence"].count("G"), row["primer_sequence"].count("C")
        row["gc_percentage"] = round(
            (nG + nC) / float(row["length"]) * 100, 2
        )  # convert to float to avoid int division

        # calculate & add Melt Temperature (Tm)
        row["melt_temperature"] = tm_calc(row["primer_sequence"])

        # Calculate raw scores for Tm (targeting 62 C) and GC% (targeting 50%)
        row["melt_temp_target_distance"] = abs(62 - row["melt_temperature"])
        row["gc_percentage_target_distance"] = abs(50 - row["gc_percentage"])

        scored_primer_option_row_list.append(row)

    raw_score_df = pd.DataFrame(scored_primer_option_row_list)

    #
    primer_group = raw_score_df.groupby("primer_name")

    total_score_row_list = []
    for primer_name, primer_group_df in primer_group:
        max_melt_temp_target_distance = primer_group_df[
            "melt_temp_target_distance"
        ].max()
        max_gc_percent_target_distance = primer_group_df[
            "gc_percentage_target_distance"
        ].max()

        # Ensure that divisor won't be 0
        assert max_melt_temp_target_distance != 0
        assert (
            max_gc_percent_target_distance != 0
        )  # failure here means that all options had exactly 50% GC - not possible

        for index, row in primer_group_df.iterrows():
            row["melt_temperature_score"] = 1 - (
                row["melt_temp_target_distance"] / max_melt_temp_target_distance
            )
            row["gc_percentage_score"] = 1 - (
                row["gc_percentage_target_distance"] / max_gc_percent_target_distance
            )

            # calculate total score by adding normalized scores and GC clamp point. Currently weighting Tm Score 2X
            row["total_score"] = (
                row["gc_clamp"]
                + 2 * row["melt_temperature_score"]
                + row["gc_percentage_score"]
            )

            # add completed row to list for final dataframe
            total_score_row_list.append(row)

    total_score_df = pd.DataFrame(total_score_row_list)

    # Add rank by total score for each option within each primer group
    scored_primer_group = total_score_df.groupby("primer_name")

    final_rank_df_list = []
    for scored_primer_name, scored_primer_group_df in scored_primer_group:
        sorted_total_score_series = scored_primer_group_df["total_score"].sort_values(
            ascending=False, ignore_index=True
        )
        total_score_rank_df = sorted_total_score_series.to_frame(
            name="total_score"
        ).reset_index(names="option_group_rank")
        total_score_rank_df["option_group_rank"] = (
            total_score_rank_df["option_group_rank"] + 1
        )
        primer_group_final_rank_df = scored_primer_group_df.merge(
            total_score_rank_df, on="total_score"
        )
        final_rank_df_list.append(primer_group_final_rank_df)

    all_options_ranked_df = pd.concat(final_rank_df_list)
    all_options_ranked_df.reset_index(drop=True, inplace=True)

    # subset all Rank #1 options into final results dataframe
    optimal_primer_results_df = all_options_ranked_df[
        all_options_ranked_df["option_group_rank"] == 1
    ]
    optimal_primer_results_df.reset_index(drop=True, inplace=True)

    if add_overhangs:
        forward_results = optimal_primer_results_df[
            optimal_primer_results_df["direction"] == "forward"
        ]
        reverse_results = optimal_primer_results_df[
            optimal_primer_results_df["direction"] == "reverse"
        ]

        forward_results["primer_sequence"] = (
            upstream_overhang + forward_results["primer_sequence"]
        )
        reverse_results["primer_sequence"] = (
            downstream_overhang + reverse_results["primer_sequence"]
        )
        print("Overhangs Added")
        optimal_primer_results_df = pd.concat(
            [forward_results, reverse_results]
        ).sort_index()

    return all_options_ranked_df, optimal_primer_results_df


def process_csv(file_object_in):
    """
    TODO: add docstring
    """
    content = file_object_in.read().decode("utf-8")
    input_df = pd.read_csv(StringIO(content))

    # check that input_df meets assumptions

    # check input columns match expected
    try:
        expected_columns = ["amplicon name", "sequence"]
        for col in list(input_df.columns):
            assert col in expected_columns
    except:
        error_message_str = f"Exptected columns {expected_columns}, but {list(input_df.columns)} detected"
        # If assumption not met, return input_valid as False,
        # error message in place of input_df, and output_df as None
        return False, error_message_str, None

    # TODO: add more input validation checks
    # try:
    #     input_dtypes = list(set(list(input_df.dtypes.values)))
    #     for dtype in input_dtypes:
    #         assert dtype == "int64" or dtype == "float64"
    # except:
    #     error_message_str = f"Exptected numeric values, but non-numeric value detected"
    #     # If assumption not met, return input_valid as False,
    #     # error message in place of input_df, and output_df as None
    #     return False, error_message_str, None

    # run primer generation function to generate output dfs from input
    all_options_ranked_df, optimal_primer_results_df = generate_primers(input_df)

    # return input_valid as True if assumptions met, input_df, and output_df
    return True, input_df, all_options_ranked_df, optimal_primer_results_df
