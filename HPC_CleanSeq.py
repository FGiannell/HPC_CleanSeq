from flask import Flask, render_template, redirect, flash, request, make_response, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import time
from werkzeug.utils import secure_filename
from pyscripts.allowed_file import allowedFile, fileExtension
from pyscripts.ex_centrifuge import (
    uploadReads, 
    executeCentrifuge, 
    downloadCentrifugeReport
)
from pyscripts.ex_recentrifuge import (
    executeRecentrifuge, 
    uploadRecentrifugeScript, 
    downloadRecentrifugeReport
)
from pyscripts.ex_rextract import (
    uploadRextractScript, 
    executeRextract, 
    downloadRextractSequences
)
from pyscripts.data_visualization import (
    createAbundancePieChart, 
    createTSVDictionary, 
    createUniquereadsBarChart, 
    createSankeyChart, 
    createNumreadsNumuniquereadsScatterChart, 
    createGenomesizeAbundanceBarChart,
    getMetrics
)


app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024 * 1024  # 20 GB
CORS(app)
socketio = SocketIO(app)


# Global variables
progress = {'state': '', 'value': 0}
HOSTNAME = ''
USERNAME = ''
PASSWORD = ''
ACCOUNT = ''
abu_chart = None
uni_rea_bar_chart = None
reads_scatter_chart = None
genomesize_abundance_bar_chart = None
hierarchy_sunkey_chart = None
metrics = None
dict = {}


@app.route("/")
def main():
    """Display the main page (Entry point).
    """
    return render_template('main.html')


@socketio.on('progress_request')
def emitProgress():
    """Function to send progress data for progress bar using socket.
    """
    global progress

    while True:
        if progress['value'] == 100:
            emit('progress', progress)
            time.sleep(1)
            break
        else:
            emit('progress', progress)
            time.sleep(1)


@app.route('/check-report', methods=['GET'])
def checkReportExists():
    """Check if there is already a centrifuge_report.tsv file downloaded.
    """
    if os.path.exists('download/centrifuge_report.tsv'):
        return jsonify({'exists': True})
    else:
        return jsonify({'exists': False})
    
    
@app.route('/download-report')
def downloadReport():
    """
    """
    # Path of the centrifuge report
    filepath = 'download/centrifuge_report.tsv'
    
    # Check if the file is present
    if os.path.exists(filepath):
        # Start download of the file
        return send_file(
            filepath, 
            as_attachment = True, 
            download_name = 'centrifuge_report.tsv'
        )
    else:
        # Send file not found error page
        return jsonify({'error': 'File non trovato.'}), 404


@app.route("/centrifuge-form")
def renderCentrifugeForm():
    """Display Centrifuge form page.
    """
    return render_template('cen_form.html')


@app.route("/centrifuge-form", methods=['POST'])
async def submitCentrifugeForm():
    """Function to get data from the form and execute Centrifuge.
    """
    global progress
    global HOSTNAME
    global USERNAME
    global PASSWORD
    global ACCOUNT
    global abu_chart
    global uni_rea_bar_chart
    global reads_scatter_chart
    global genomesize_abundance_bar_chart
    global hierarchy_sunkey_chart
    global metrics
    global dict

    HOSTNAME = request.form['hostname']
    USERNAME = request.form['username']
    PASSWORD = request.form['password']
    ACCOUNT = request.form['account']

    reads_files = request.files.getlist('readsFiles')

    read_type = request.form['readType']
    domains = request.form.getlist('domains')

    abs_paths = []

    # Check at least one domain selected
    if len(domains) == 0:
        flash("At least one domain must be selected")
        return redirect(request.url)

    # Check if files are selected according to paired or single end selector
    if read_type == 'single' and len(reads_files) != 1:
        flash("If single-end reads selected, one file must be uploaded")
        return redirect(request.url)
    elif read_type == 'paired' and len(reads_files) != 2:
        flash("If paired-end reads selected, two files must be uploaded")
        return redirect(request.url)

    # Check if the files are in the correct format (fastq or fastq.gz)
    for reads in reads_files:
        file_ext = fileExtension(reads.filename)
        if file_ext != 'fastq' and file_ext != 'fastq.gz':
            flash(
                "Selected files are in the wrong format "
                "(accepted fastq or fastq.gz)"
            )
            return redirect(request.url)

    # Upload files in the 'uploads' folder
    for reads in reads_files:
        filename = secure_filename(reads.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        reads.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        # Get paths of the file
        abs_paths.append(os.path.abspath(file_path))

    # Upload reads files in the cluster
    progress = {'state': 'Uploading reads files', 'value': 10}
    await uploadReads(HOSTNAME, USERNAME, PASSWORD, ACCOUNT, abs_paths)

    # Execute Centrifuge on the cluster
    progress = {'state': 'Executing Centrifuge', 'value': 60}
    await executeCentrifuge(HOSTNAME, USERNAME, PASSWORD, domains)

    # Get the Centrifuge report from the cluster
    progress = {'state': 'Downloading Centrifuge report', 'value': 90}
    await downloadCentrifugeReport(HOSTNAME, USERNAME, PASSWORD)
    progress = {'state': 'Downloading Centrifuge report', 'value': 100}
    time.sleep(3)

    # Generate the dictionary from the tsv file
    dict = createTSVDictionary('download/centrifuge_report.tsv')
    
    # Generate all charts from the dictionary
    abu_chart = createAbundancePieChart(dict)
    uni_rea_bar_chart = createUniquereadsBarChart(dict)
    reads_scatter_chart = createNumreadsNumuniquereadsScatterChart(dict)
    genomesize_abundance_bar_chart = createGenomesizeAbundanceBarChart(dict)
    hierarchy_sunkey_chart = createSankeyChart(dict)
    metrics = getMetrics(dict)
    
    # Display report page
    return render_template(
        'report_tsv_page.html', 
        abu_chart = abu_chart,
        reads_scatter_chart = reads_scatter_chart,
        uni_rea_bar_chart = uni_rea_bar_chart,
        genomesize_abundance_bar_chart = genomesize_abundance_bar_chart,
        hierarchy_sunkey_chart = hierarchy_sunkey_chart,
        metrics = metrics,
        rec_button = True,
        rex_button = True,
        dict = dict
    )


# Function to display the upload report analisys page
@app.route("/report-analisys")
def report():
    """Function to display the upload report analisys page.
    """
    return render_template('report_page.html')


@app.route("/report-analisys", methods=['POST'])
def reportUpload():
    """Handle the post method of uploading the tsv 
    report file by the user and display report page.
    """
    global abu_chart
    global uni_rea_bar_chart
    global reads_scatter_chart
    global genomesize_abundance_bar_chart
    global hierarchy_sunkey_chart
    global metrics
    global dict

    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    if file and allowedFile(file.filename):
        # Upload file in the 'uploads' folder
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash('File successfully uploaded')

        # Generate the dictionary from the tsv file
        dict = createTSVDictionary(filepath)
        
        # Generate all charts from the dictionary
        abu_chart = createAbundancePieChart(dict)
        uni_rea_bar_chart = createUniquereadsBarChart(dict)
        reads_scatter_chart = createNumreadsNumuniquereadsScatterChart(dict)
        genomesize_abundance_bar_chart = createGenomesizeAbundanceBarChart(dict)
        hierarchy_sunkey_chart = createSankeyChart(dict)
        metrics = getMetrics(dict)
        
        # Display report page
        return render_template(
            'report_tsv_page.html', 
            abu_chart = abu_chart,
            reads_scatter_chart = reads_scatter_chart,
            uni_rea_bar_chart = uni_rea_bar_chart,
            genomesize_abundance_bar_chart = genomesize_abundance_bar_chart,
            hierarchy_sunkey_chart = hierarchy_sunkey_chart,
            metrics = metrics,
            rec_button = False,
            rex_button = False,
            dict = dict
        )
    else:
        flash('Allowed file type is TSV')
        return redirect(request.url)


@app.route("/recentrifuge-submit")
async def submitRecentrifuge():
    """Function to handle the 'Execute Recentrifuge' button in the 
    tsv report page and display the Recentrifuge HTML report page.
    """
    global progress
    global HOSTNAME
    global USERNAME
    global PASSWORD
    global ACCOUNT

    # Upload Recentrifuge script in the cluster
    progress = {'state': 'Uploading Recentrifuge script', 'value': 10}
    await uploadRecentrifugeScript(HOSTNAME, USERNAME, PASSWORD, ACCOUNT)
    
    # Execute Recentrifuge on the cluster
    progress = {'state': 'Executing Recentrifuge', 'value': 60}
    await executeRecentrifuge(HOSTNAME, USERNAME, PASSWORD)
    
    # Get the Centrifuge report from the cluster
    progress = {'state': 'Downloading Recentrifuge report page', 'value': 90}
    await downloadRecentrifugeReport(HOSTNAME, USERNAME, PASSWORD)
    progress = {'state': 'Downloading Recentrifuge report page', 'value': 100}
    time.sleep(3)

    # Display the Recentrifuge report HTML page
    return render_template('recentrifuge_output.html')


@app.route("/rextract-submit")
async def submitRextract():
    """Function to upload, execute Rextract script and download Rextract 
    cleaned sequences.
    """
    global progress
    global HOSTNAME
    global USERNAME
    global PASSWORD
    global ACCOUNT

    # Upload Rextract script in the cluster
    progress = {'state': 'Uploading Rextract script', 'value': 10}
    await uploadRextractScript(HOSTNAME, USERNAME, PASSWORD, ACCOUNT)
    
    # Execute Rextract on the cluster
    progress = {'state': 'Executing Rextract', 'value': 60}
    await executeRextract(HOSTNAME, USERNAME, PASSWORD)

    # Get the Rextract cleaned sequences from the cluster
    progress = {'state': 'Downloading cleaned sequences', 'value': 90}
    await downloadRextractSequences(HOSTNAME, USERNAME, PASSWORD)
    progress = {'state': 'Downloading cleaned sequences', 'value': 100}
    time.sleep(3)

    # Check if the file is present
    if os.path.exists('download/cleaned_sequences.tar.gz'):
        # Start download of the file
        return send_file(
            'download/cleaned_sequences.tar.gz', 
            as_attachment = True, 
            download_name = 'cleaned_sequences.tar.gz'
        )
    else:
        # Send file not found error page
        return jsonify({'error': 'File non trovato.'}), 404



if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    socketio.run(app, host = '127.0.0.1', port = 3000)
