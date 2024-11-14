
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import csv
import random

# Set the theme style for all charts
pio.templates.default = "ggplot2"

SUPERKINGDOM = 0
PHYLUM = 1
CLASS = 2
ORDER = 3
FAMILY = 4
GENUS = 5
SPECIES = 6
LEAF = 7


def createGenomesizeAbundanceBarChart(dictionary):
    """Function to generate bar chart (genomeSize vs Abundance).
    """
    keys = list(dictionary.keys())
    genomesizes = []
    abundances = []

    for key in keys:
        genomeSize = dictionary[key]['genomeSize']
        abundance = dictionary[key]['abundance']

        genomesizes.append(genomeSize)
        abundances.append(abundance)

    # Create figure
    fig = make_subplots(rows = 2, cols = 1, shared_xaxes = True)

    # Add numReads trace
    fig.append_trace(
        go.Bar(
            x = keys,
            y = abundances,
            name = 'Abundance'
        ),
        row = 1,
        col = 1
    )

    # Add numUniqueReads trace
    fig.append_trace(
        go.Bar(
            x = keys,
            y = genomesizes,
            name = 'Genome size'
        ),
        row = 2,
        col = 1
    )

    fig.update_layout(
        yaxis_title="Number of reads"
    )
    fig.update_xaxes(title_text="Organism", row=2, col=1)

    # Convert the chart in html
    chart_HTML = pio.to_html(fig, full_html=False)

    return chart_HTML


def createNumreadsNumuniquereadsScatterChart(dictionary):
    """Function to generate scatter plot chart (numReads vs numUniqueReads).
    """
    keys = list(dictionary.keys())
    num_reads = []
    num_unique_reads = []

    for key in keys:
        read = dictionary[key]['numReads']
        unique_read = dictionary[key]['numUniqueReads']

        num_reads.append(read)
        num_unique_reads.append(unique_read)

    # Create figure
    fig = go.Figure()

    # Add numReads trace
    fig.add_trace(
        go.Scatter(
            x = keys,
            y = num_reads,
            name = 'Number of reads',
            mode = 'markers'
        )
    )

    # Add numUniqueReads trace
    fig.add_trace(
        go.Scatter(
            x = keys,
            y = num_unique_reads,
            name = 'Number of unique reads',
            mode = 'markers'
        )
    )

    fig.update_layout(
        yaxis_title="Number of reads",
        xaxis_title="Organism"
    )

    # Convert the chart in html
    chart_HTML = pio.to_html(fig, full_html=False)

    return chart_HTML


def createAbundancePieChart(dict):
    """Function to generate pie chart (abundance).
    """
    keys = list(dict.keys())
    names = []
    values = []
    
    # Select only values and names with abundance > 0.0
    for key in keys:
        value = dict[key]['abundance']
        if value > 0.0:
            names.append(key)
            values.append(value)

    # Create the figure
    fig = go.Figure(
        data=[
            go.Pie(
                labels=names, 
                values=values, 
                textinfo='label+percent', 
                insidetextorientation='radial',
                hole=.3
            )
        ]
    )

    # Convert the chart in html
    chart_html = pio.to_html(fig, full_html=False)  

    return chart_html


def createUniquereadsBarChart(dict):
    """Function to generate bar chart (unique reads).
    """
    keys = list(dict.keys())
    values = []
    names = []
    unique_reads = []

    for key in keys:
        values.append(dict[key]['numUniqueReads'])

    # Remove values under 1000 reads
    for i in range(len(values)):
        if values[i] > 1000:
            names.append(keys[i])
            unique_reads.append(values[i])

    # Create chart figure
    fig = go.Figure(
        data=[
            go.Bar(
                x=names, 
                y=unique_reads
            )
        ]
    )
    fig.update_layout(
        yaxis_title="Unique Reads",
        xaxis_title="Organism"
    )

    # Convert the chart in html
    chart_html = pio.to_html(fig, full_html=False)  

    return chart_html


def createSankeyChart(dictionary):
    """Function to generate sankey chart (organism hierarchy).
    """
    keys = list(dictionary.keys())
    source = []
    dest = []
    values = []
    colors = []

    for i in range(len(keys)):
        taxrank = dictionary[keys[i]]['taxRank']
        classrank = 0

        # Assign classrank to current organism
        if taxrank == 'superkingdom':
            classrank = SUPERKINGDOM
        if taxrank == 'phylum':
            classrank = PHYLUM
        if taxrank == 'class':
            classrank = CLASS
        if taxrank == 'order':
            classrank = ORDER
        if taxrank == 'family':
            classrank = FAMILY
        if taxrank == 'genus':
            classrank = GENUS
        if taxrank == 'species':
            classrank = SPECIES
        if taxrank == 'leaf':
            classrank = LEAF

        # Set the value of j
        j = i + 1

        # Search for destinations (aka direct discendents for the organism)
        for k in range(j, len(keys)):
            nextrank = dictionary[keys[k]]['taxRank']
            next_genomesize = dictionary[keys[k]]['genomeSize']

            # Assign classrank to each organism
            if nextrank == 'superkingdom':
                next_classrank = SUPERKINGDOM
            if nextrank == 'phylum':
                next_classrank = PHYLUM
            if nextrank == 'class':
                next_classrank = CLASS
            if nextrank == 'order':
                next_classrank = ORDER
            if nextrank == 'family':
                next_classrank = FAMILY
            if nextrank == 'genus':
                next_classrank = GENUS
            if nextrank == 'species':
                next_classrank = SPECIES
            if nextrank == 'leaf':
                next_classrank = LEAF

            if next_classrank > classrank:
                # Add link
                source.append(i)
                dest.append(k)
                values.append(next_genomesize)
                #print(f"{keys[i]} [{taxrank}] -> {keys[k]} [{nextrank}]")
            else:
                break
    
    # Generate random colors for diagram's nodes
    for i in range(len(source)):
        # Generate color based on index
        r = random.randint(1, 255)
        g = random.randint(1, 255)
        b = 128                                     # Fixed value for blue
        colors.append(f'rgba({r}, {g}, {b}, 1)')

    # Generate link's colors
    link_colors = [color.replace('1)', '0.4)') for color in colors]

    # Create chart figure
    fig = go.Figure(
        data=[
            go.Sankey(
                valueformat = ".0f",
                # Define nodes
                node = dict(
                    pad = 15,
                    thickness = 15,
                    line = dict(color = "black", width = 0.5),
                    label = keys,
                    color = colors
                ),
                # Add links
                link = dict(
                    source = source, 
                    target = dest,
                    value = [g if g > 0 else 1 for g in values],
                    color = link_colors, 
                    hovercolor = colors
                )
            )
        ]
    )
    fig.update_layout(height=1500)

    # Convert the chart in html
    chart_html = pio.to_html(fig, full_html=False)  

    return chart_html


def getMetrics(dict):
    """Function to get relevant values.
    """
    keys = dict.keys()
    max_abundance = 0.0
    max_num_reads = 0
    max_num_uniquereads = 0
    max_genomesize = 0
    max_abundance_name = ''
    max_num_reads_name = ''
    max_num_uniquereads_name = ''
    max_genomesize_name = ''

    for key in keys:
        abundance = dict[key]['abundance']
        num_reads = dict[key]['numReads']
        num_uniquereads = dict[key]['numUniqueReads']
        genomesize = dict[key]['genomeSize']

        # Update max values
        if abundance > max_abundance:
            max_abundance = abundance
            max_abundance_name = key
        
        if num_reads > max_num_reads:
            max_num_reads = num_reads
            max_num_reads_name = key

        if num_uniquereads > max_num_uniquereads:
            max_num_uniquereads = num_uniquereads
            max_num_uniquereads_name = key

        if genomesize > max_genomesize:
            max_genomesize = genomesize
            max_genomesize_name = key

    # Convert max_abundance in percentage
    max_abundance_perc = round(max_abundance * 100)

    return [[max_abundance_name, max_abundance_perc], 
            [max_num_reads_name, max_num_reads], 
            [max_num_uniquereads_name, max_num_uniquereads], 
            [max_genomesize_name, max_genomesize]]


def createTSVDictionary(filepath):
    """Function to create dictionary out of the report.tsv file.
    """
    # Empty dictionary
    dict = {}

    # Open the file in binary reading (data file)
    with open(filepath, 'r') as file:
        reader = csv.DictReader(file, delimiter='\t')

        for row in reader:
            name = row['name']
            dict[name] = {
                'taxID': row['taxID'],
                'taxRank': row['taxRank'],
                'genomeSize': int(row['genomeSize']),
                'numReads': int(row['numReads']),
                'numUniqueReads': int(row['numUniqueReads']),
                'abundance': float(row['abundance'])
            }

    return dict

