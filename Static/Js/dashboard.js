// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard script loaded');

    const docTypeSelect = document.getElementById('docTypeSelect');
    const cinUploadContainer = document.getElementById('cinUploadContainer');
    const singleUploadContainer = document.getElementById('singleUploadContainer');
    const contractUploadContainer = document.getElementById('contractUploadContainer');

    const fileInputFront = document.getElementById('fileInputFront');
    const fileInputBack = document.getElementById('fileInputBack');
    const fileInputSingle = document.getElementById('fileInputSingle');
    const fileInputContract = document.getElementById('fileInputContract');

    const documentPreviewContainer = document.getElementById('documentPreviewContainer');
    const extractedData = document.getElementById('extractedData');
    const verificationResults = document.getElementById('verificationResults');

    const uploadButton = document.getElementById('uploadButton');
    const uploadButtonText = document.getElementById('uploadButtonText');
    const loadingSpinner = document.getElementById('loadingSpinner');
// ================= EDIT STATE =================
  let editableExtractedData = null;
  let editableDocType = null;
  let currentRecordId = null;
    // ---------------- UI Switch ----------------
    function updateDocTypeUI() {
        const docType = docTypeSelect.value;
        cinUploadContainer.style.display = docType === 'cin' ? 'block' : 'none';
        singleUploadContainer.style.display = docType === 'passport' ? 'block' : 'none';
        contractUploadContainer.style.display = docType === 'contract' ? 'block' : 'none';


        fileInputFront.value = '';
        fileInputBack.value = '';
        fileInputSingle.value = '';
        fileInputContract.value = '';

        clearPreview();
        extractedData.innerHTML = '';
        verificationResults.innerHTML = '';
    }

    updateDocTypeUI();
    docTypeSelect.addEventListener('change', updateDocTypeUI);

    // ---------------- Drag & Drop ----------------
    function setupDropzone(dropzone, fileInput) {
        if (!dropzone || !fileInput) return;

        dropzone.addEventListener('click', () => fileInput.click());

        dropzone.addEventListener('dragover', e => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });

        dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));

        dropzone.addEventListener('drop', e => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                previewFiles();
            }
        });

        fileInput.addEventListener('change', previewFiles);
    }

    setupDropzone(document.querySelector('label[for="fileInputFront"]'), fileInputFront);
    setupDropzone(document.querySelector('label[for="fileInputBack"]'), fileInputBack);
    setupDropzone(document.querySelector('label[for="fileInputSingle"]'), fileInputSingle);
    setupDropzone(document.querySelector('label[for="fileInputContract"]'), fileInputContract);

    // ---------------- Preview ----------------
    function previewFiles() {
        documentPreviewContainer.innerHTML = '';
        const docType = docTypeSelect.value;

        if (docType === 'cin') {
            [fileInputFront.files[0], fileInputBack.files[0]].forEach(file => {
                if (file && file.type.startsWith('image/')) addImagePreview(file, 250);
            });
        } else if (docType === 'passport') {
            const file = fileInputSingle.files[0];
            if (file && file.type.startsWith('image/')) addImagePreview(file, 400);
        } else if (docType === 'contract') {
            const file = fileInputContract.files[0];
            if (file && file.type === 'application/pdf') {
                addPDFPreview(file);
            }
        }
    }

    function addImagePreview(file, maxHeight) {
        const img = document.createElement('img');
        img.src = URL.createObjectURL(file);
        img.className = 'img-fluid';
        img.style.maxHeight = maxHeight + 'px';
        img.style.border = '1px solid #ddd';
        img.style.borderRadius = '8px';
        img.style.objectFit = 'contain';
        img.style.marginRight = '10px';
        img.style.marginBottom = '10px';
        documentPreviewContainer.appendChild(img);
    }

    function addPDFPreview(file) {
        documentPreviewContainer.innerHTML = '<p class="text-muted"><i class="fa-solid fa-spinner fa-spin"></i> Loading PDF preview...</p>';

        const fileURL = URL.createObjectURL(file);

        pdfjsLib.getDocument(fileURL).promise.then(pdf => {
            documentPreviewContainer.innerHTML = '';

            const totalPages = pdf.numPages;
            const pagesToShow = Math.min(totalPages, 5);

            const pagesContainer = document.createElement('div');
            pagesContainer.style.cssText = 'display:flex;flex-direction:column;gap:10px;align-items:center;';

            const pageInfo = document.createElement('div');
            pageInfo.style.cssText = 'color:#e8b4d3;font-size:0.85em;margin-bottom:10px;';
            pageInfo.textContent = `Showing ${pagesToShow} of ${totalPages} pages`;
            pagesContainer.appendChild(pageInfo);

            for (let pageNum = 1; pageNum <= pagesToShow; pageNum++) {
                pdf.getPage(pageNum).then(page => {
                    const scale = 1.2;
                    const viewport = page.getViewport({ scale });

                    const canvas = document.createElement('canvas');
                    canvas.style.cssText = 'border:1px solid #555;border-radius:4px;max-width:100%;margin-bottom:10px;';
                    const context = canvas.getContext('2d');
                    canvas.height = viewport.height;
                    canvas.width = viewport.width;

                    page.render({ canvasContext: context, viewport: viewport });
                    pagesContainer.appendChild(canvas);
                });
            }

            documentPreviewContainer.appendChild(pagesContainer);
        }).catch(err => {
            console.error('PDF load error:', err);
            documentPreviewContainer.innerHTML = '<p class="text-danger">Failed to load PDF preview.</p>';
        });
    }

    function clearPreview() {
        documentPreviewContainer.innerHTML = '';
    }

    // ---------------- Upload ----------------
    uploadButton.addEventListener('click', () => {
        const docType = docTypeSelect.value;
        const formData = new FormData();
        let endpoint = '';

        if (docType === 'cin') {
            if (!fileInputFront.files[0] || !fileInputBack.files[0]) {
                alert('Please select both front and back images for CIN');
                return;
            }
            formData.append('front', fileInputFront.files[0]);
            formData.append('back', fileInputBack.files[0]);
            endpoint = '/ocr/upload/cin';
        } else if (docType === 'passport') {
            if (!fileInputSingle.files[0]) {
                alert('Please select an image file for Passport');
                return;
            }
            formData.append('file', fileInputSingle.files[0]);
            endpoint = '/ocr/upload/passport';
        } else if (docType === 'contract') {
            if (!fileInputContract.files[0]) {
                alert('Please select a PDF file for Contract');
                return;
            }
            formData.append('file', fileInputContract.files[0]);
            endpoint = '/ocr/upload/pdf';
        }

        uploadButton.disabled = true;
        uploadButtonText.style.display = 'none';
        loadingSpinner.style.display = 'inline-block';

        fetch(endpoint, {
            method: 'POST',
            body: formData,
            credentials: 'include'
        })
        .then(res => {
            console.log('=== RESPONSE INFO ===');
            console.log('Status:', res.status);
            console.log('OK:', res.ok);

            if (!res.ok) {
                throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            }

            return res.text(); // Get as text first to debug
        })
        .then(text => {
            console.log('=== RAW RESPONSE ===');
            console.log('Length:', text.length, 'characters');
            console.log('Size:', (text.length / 1024).toFixed(2), 'KB');
            console.log('First 200 chars:', text.substring(0, 200));

            // Try to parse JSON
            let data;
            try {
                data = JSON.parse(text);
            } catch (e) {
                console.error('JSON Parse Error:', e);
                console.error('Failed at position:', e.message);
                throw new Error('Server returned invalid JSON');
            }

            console.log('=== PARSED DATA ===');
            console.log('Keys:', Object.keys(data));
            console.log('Success:', data.success);
            console.log('Message:', data.message);

            // Deep inspection of extracted_data
            if (data.extracted_data) {
                console.log('=== EXTRACTED_DATA ===');
                console.log('Keys:', Object.keys(data.extracted_data));
                console.log('Filename:', data.extracted_data.filename);
                console.log('Total pages:', data.extracted_data.total_pages);
                console.log('Tables count:', data.extracted_data.tables_count);
                console.log('Images count:', data.extracted_data.images_count);
                console.log('Has pages array:', Array.isArray(data.extracted_data.pages));
                console.log('Pages array length:', data.extracted_data.pages?.length);

                // Check each page for images
                if (data.extracted_data.pages) {
                    let totalImagesFound = 0;
                    let imagesWithValidBase64 = 0;

                    data.extracted_data.pages.forEach((page, pageIdx) => {
                        console.log(`\n--- Page ${page.page_number} ---`);
                        console.log('  Content items:', page.content?.length || 0);

                        if (page.content) {
                            const textItems = page.content.filter(i => i.type === 'text').length;
                            const tableItems = page.content.filter(i => i.type === 'table').length;
                            const imageItems = page.content.filter(i => i.type === 'image');

                            console.log(`  Text blocks: ${textItems}, Tables: ${tableItems}, Images: ${imageItems.length}`);

                            imageItems.forEach((img, imgIdx) => {
                                totalImagesFound++;
                                const hasBase64 = !!img.base64;
                                const base64Length = img.base64?.length || 0;
                                const startsCorrectly = img.base64?.startsWith('data:image/');
                                const isValid = hasBase64 && base64Length > 100 && startsCorrectly;

                                if (isValid) imagesWithValidBase64++;

                                console.log(`  Image ${img.image_number}:`, {
                                    format: img.format,
                                    hasBase64: hasBase64,
                                    base64Length: base64Length,
                                    startsCorrectly: startsCorrectly,
                                    isValid: isValid,
                                    preview: img.base64?.substring(0, 50) + '...'
                                });

                                if (!isValid) {
                                    console.error(`  ❌ Image ${img.image_number} has INVALID base64!`);
                                }
                            });
                        }
                    });

                    console.log(`\n=== IMAGE SUMMARY ===`);
                    console.log(`Total images found: ${totalImagesFound}`);
                    console.log(`Images with valid base64: ${imagesWithValidBase64}`);
                    console.log(`Invalid images: ${totalImagesFound - imagesWithValidBase64}`);
                } else {
                    console.error('❌ NO PAGES ARRAY IN EXTRACTED_DATA!');
                }
            } else {
                console.error('❌ NO EXTRACTED_DATA IN RESPONSE!');
            }

            // Store record ID if available
currentRecordId = data.record_id || null;

let content;
if (docType === 'contract') {
    content = {
        text: data.text || '',
        tables: data.tables || [],
        images: data.images || [],
        pages: data.extracted_data?.pages || [] // Keep the pages structure
    };
} else {
    // Check both potential keys: extracted_data OR extracted_text
    content = data.extracted_data || data.extracted_text || {};
}



if (!content || typeof content !== 'object') {
    console.warn('Extracted data missing or invalid, using empty object.');
    content = {};
}
// Deep clone safely
editableExtractedData = structuredClone(content); // Modern alternative to JSON.parse(JSON.stringify())
editableDocType = docType;

displayExtractedData(content, docType);


            if (data.verification !== undefined && data.verification !== null) {
                displayVerificationResults(data.verification);
            } else {
                verificationResults.innerHTML = '<p class="text-muted">No verification performed for this document type.</p>';
            }
        })
        .catch(err => {
            console.error('=== ERROR ===');
            console.error('Error type:', err.name);
            console.error('Error message:', err.message);
            console.error('Stack:', err.stack);

            alert('Upload failed: ' + err.message);
            verificationResults.innerHTML = `<div class="alert alert-danger">Upload failed: ${err.message}</div>`;
        })
        .finally(() => {
            uploadButton.disabled = false;
            uploadButtonText.style.display = 'inline';
            loadingSpinner.style.display = 'none';
        });
    });

    // ---------------- Display Extracted Data ----------------


// Replace your displayExtractedData function with this:

function displayExtractedData(data, docType) {
    extractedData.innerHTML = '';
    if (!data || Object.keys(data).length === 0) {
        extractedData.innerHTML = '<p class="text-muted">No data extracted.</p>';
        return;
    }

    const container = document.createElement('div');
    container.className = 'extracted-content';

    // Handle PDF/Contract documents with pages array
    // Handle PDF/Contract documents with pages array OR fallback text
if ((data.pages && Array.isArray(data.pages) && data.pages.length > 0) || data.text) {
    // First show text if available
    if (data.text) {
        const pre = document.createElement('pre');
        pre.textContent = data.text;
        pre.style.cssText = `
            margin-bottom: 1rem;
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: inherit;
            font-size: 0.95rem;
            line-height: 1.6;
            color: #333;
        `;
        container.appendChild(pre);
    }

    // Then show pages if available
    if (data.pages && Array.isArray(data.pages)) {
        data.pages.forEach(page => {
            if (!page.content) return;

            const pageDiv = document.createElement('div');
            pageDiv.style.cssText = 'margin-bottom:2rem; border-bottom:1px dashed #ccc; padding-bottom:1rem;';

            const pageTitle = document.createElement('h5');
            pageTitle.textContent = `Page ${page.page_number || '?'}:`;
            pageTitle.style.cssText = 'margin-bottom:0.5rem; color:#e8b4d3;';
            pageDiv.appendChild(pageTitle);

            page.content.forEach(item => {
                if (item.type === 'text' && item.value) {
                    const pre = document.createElement('pre');
                    pre.textContent = item.value;
                    pre.style.cssText = `
                        margin-bottom: 1rem;
                        white-space: pre-wrap;
                        word-wrap: break-word;
                        font-family: inherit;
                        font-size: 0.95rem;
                        line-height: 1.6;
                        background: transparent;
                        border: none;
                        padding: 0;
                        color: #333;
                    `;
                    pageDiv.appendChild(pre);
                } else if (item.type === 'table') {
                    // table rendering code...
                } else if (item.type === 'image' && item.base64) {
                    // image rendering code...
                }
            });

            container.appendChild(pageDiv);
        });
    }
} else {

        // Handle CIN and Passport documents (flat key-value structure)
        Object.entries(data).forEach(([key, value]) => {
            if (shouldSkipEditField(key, value)) return;

            // Arabic text detection
            const isArabic = typeof value === 'string' && /[\u0600-\u06FF]/.test(value);

            if (key === 'text') {
                const textBlock = document.createElement('pre');
                textBlock.textContent = value;
                textBlock.style.cssText = `
                    margin-bottom: 1rem;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                    font-family: inherit;
                    font-size: 0.95rem;
                    line-height: 1.6;
                    color: #333;
                    direction: ${isArabic ? 'rtl' : 'ltr'};
                `;
                container.appendChild(textBlock);
                return;
            }

            // Create a row for each field
            const fieldRow = document.createElement('div');
            fieldRow.style.cssText = `
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 16px;
                margin-bottom: 8px;
                background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
                border-left: 4px solid #667eea;
                border-radius: 6px;
                transition: all 0.3s ease;
                direction: ${isArabic ? 'rtl' : 'ltr'};
            `;

            // Hover effect
            fieldRow.addEventListener('mouseenter', () => {
                fieldRow.style.background = 'linear-gradient(135deg, #667eea25 0%, #764ba225 100%)';
                fieldRow.style.transform = 'translateX(4px)';
            });
            fieldRow.addEventListener('mouseleave', () => {
                fieldRow.style.background = 'linear-gradient(135deg, #667eea15 0%, #764ba215 100%)';
                fieldRow.style.transform = 'translateX(0)';
            });

            const label = document.createElement('div');
            label.style.cssText = `
                font-weight: 600;
                color: #667eea;
                font-size: 0.95rem;
                flex: 0 0 40%;
                text-transform: capitalize;
                text-align: ${isArabic ? 'right' : 'left'};
            `;
            label.textContent = formatKey(key);

            const valueDiv = document.createElement('div');
            valueDiv.style.cssText = `
                color: #2d3748;
                font-size: 1rem;
                flex: 0 0 58%;
                text-align: ${isArabic ? 'left' : 'right'};
                font-weight: 500;
                word-wrap: break-word;
            `;

            if (typeof value === 'object' && value !== null) {
                valueDiv.textContent = JSON.stringify(value, null, 2);
                valueDiv.style.fontSize = '0.85rem';
                valueDiv.style.fontFamily = 'monospace';
            } else {
                valueDiv.textContent = value;
            }

            fieldRow.appendChild(label);
            fieldRow.appendChild(valueDiv);
            container.appendChild(fieldRow);
        });
    }

    extractedData.appendChild(container);
}



const editDataButton = document.getElementById('editDataButton');
const editDataForm = document.getElementById('editDataForm');
const saveEditedDataBtn = document.getElementById('saveEditedData');

editDataButton.addEventListener('click', () => {
    console.log('Edit button clicked');
    console.log('Editable data:', editableExtractedData);
    console.log('Editable doc type:', editableDocType);

    if (!editableExtractedData) {
        alert('No extracted data to edit. Please upload a document first.');
        return;
    }

    buildEditForm(editableExtractedData, editableDocType);

    // Initialize and show modal
    const modalElement = document.getElementById('editDataModal');
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
});

saveEditedDataBtn.addEventListener('click', async () => {
    applyEdits();
    displayExtractedData(editableExtractedData, editableDocType);
    saveEditedDataBtn.blur();

    const modalElement = document.getElementById('editDataModal');
    const modal = bootstrap.Modal.getInstance(modalElement);
    if (modal) modal.hide();

    showNotification('Changes saved successfully!', 'success');

    if (currentRecordId) {
        try {
            const res = await fetch(`/ocr/update/${currentRecordId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    extracted_data: editableExtractedData,
                    doc_type: editableDocType
                })
            });

            if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);

            const data = await res.json();
            console.log('Saved to backend:', data);

        } catch (err) {
            console.error('Failed to save to backend:', err);
            showNotification('Failed to save to backend: ' + err.message, 'danger');
        }
    }
});

function formatKey(key) {
    return key
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}




    // ---------------- Display Verification Results ----------------
    function displayVerificationResults(results) {
        console.log('=== VERIFICATION DISPLAY ===');
        console.log('Type:', typeof results);
 window.currentVerificationResults = results;
        verificationResults.innerHTML = '';

        if (Array.isArray(results)) {
            const alert = document.createElement('div');
            alert.className = 'alert alert-warning';
            alert.innerHTML = '<strong>⚠️ Verification Error:</strong><br>' + results.join('<br>');
            verificationResults.appendChild(alert);
            return;
        }

        if (typeof results === 'object' && results !== null) {
            const scoreCard = document.createElement('div');
            scoreCard.className = 'card mb-3';
            scoreCard.style.cssText = 'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; box-shadow: 0 8px 16px rgba(0,0,0,0.2);border:none;';

            const overallScore = results.overall_score || 0;
            const isAuthentic = results.is_authentic || false;
            const confidenceLevel = results.confidence_level || 'low';

            const statusIcon = isAuthentic ? '✅' : '❌';
            const statusText = isAuthentic ? 'Authentic' : 'Not Authentic';

            scoreCard.innerHTML = `
                <div class="card-body text-center p-4">
                    <h3 class="mb-3" style="font-weight:700;">${statusIcon} ${statusText}</h3>
                    <div style="font-size: 3.5rem; font-weight: bold; margin: 25px 0;">${overallScore}%</div>
                    <div style="font-size: 1.2rem; opacity: 0.95; text-transform: uppercase; letter-spacing: 3px;">
                        Confidence: ${confidenceLevel}
                    </div>
                </div>
            `;

            verificationResults.appendChild(scoreCard);

            if (results.checks && Object.keys(results.checks).length > 0) {
                const checksTitle = document.createElement('h6');
                checksTitle.textContent = 'Detailed Verification Checks';
                checksTitle.className = 'mt-4 mb-3';
                checksTitle.style.cssText = 'font-weight: 700; color: #333;';
                verificationResults.appendChild(checksTitle);

                const checksList = document.createElement('div');
                checksList.className = 'list-group';

                Object.entries(results.checks).forEach(([checkName, checkData]) => {
                    const item = document.createElement('div');
                    item.className = 'list-group-item';
                    item.style.cssText = 'border-left: 5px solid ' + (checkData.passed ? '#28a745' : '#dc3545') + '; margin-bottom: 12px;border-radius:6px;';

                    const passed = checkData.passed || false;
                    const score = checkData.score || 0;
                    const details = checkData.details || 'No details available';

                    const icon = passed ? '✅' : '❌';
                    const badgeClass = passed ? 'bg-success' : 'bg-danger';

                    item.innerHTML = `
                        <div class="d-flex justify-content-between align-items-start">
                            <div style="flex: 1;">
                                <div style="font-weight: 600; font-size: 1.05rem; margin-bottom: 6px;">
                                    ${icon} ${formatKey(checkName)}
                                </div>
                                <div class="text-muted small">${details}</div>
                            </div>
                            <span class="badge ${badgeClass} ms-3" style="font-size: 1rem; padding: 10px 15px;">${score} pts</span>
                        </div>
                    `;

                    checksList.appendChild(item);
                });

                verificationResults.appendChild(checksList);
            }

            if (results.error) {
                const errorAlert = document.createElement('div');
                errorAlert.className = 'alert alert-danger mt-3';
                errorAlert.innerHTML = `<strong>⚠️ Error:</strong> ${results.error}`;
                verificationResults.appendChild(errorAlert);
            }
        } else {
            verificationResults.innerHTML = '<div class="alert alert-info">No verification results available.</div>';
        }
    }
 function buildEditForm(data, docType) {
    editDataForm.innerHTML = '';

    // Handle PDF/Contract
    if (docType === 'contract' && data.text) {
        const div = document.createElement('div');
        div.className = 'mb-3';
        div.innerHTML = `
            <label class="form-label" style="color: #e8b4d3; font-weight: 600;">Extracted Text</label>
            <textarea class="form-control" rows="15" data-path="text" style="background: rgba(60, 55, 75, 0.9); color: white; border: 1px solid rgba(232, 180, 211, 0.3); border-radius: 6px;">${escapeHtml(data.text)}</textarea>
        `;
        editDataForm.appendChild(div);
        return;
    }

    // ---- PDF / CONTRACT (pages based) ----
    if (Array.isArray(data.pages)) {
        data.pages.forEach((page, pIdx) => {
            const title = document.createElement('h6');
            title.className = 'mt-3';
            title.textContent = `Page ${page.page_number || pIdx + 1}`;
            editDataForm.appendChild(title);

            page.content?.forEach((item, iIdx) => {
                if (item.type === 'text' && item.value) {
                    createTextarea(
                        `pages.${pIdx}.content.${iIdx}.value`,
                        `Text block ${iIdx + 1}`,
                        item.value
                    );
                }
            });
        });
        return;
    }

    // ---- CIN / PASSPORT (flat key-value) ----
    Object.entries(data).forEach(([key, value]) => {
        if (shouldSkipEditField(key, value)) return;

        if (typeof value === 'string' && value.length > 80) {
            createTextarea(key, formatKey(key), value);
        } else {
            createInput(key, formatKey(key), value);
        }
    });
}
// ---------------- Export Functions ----------------
function prepareDataForExport() {
    return {
        extracted_data: editableExtractedData,
        verification: currentRecordId ? null : null // optional: include verification if available
    };
}

// PDF
document.getElementById('downloadPDF').addEventListener('click', () => {
    if (!editableExtractedData) return alert('No data to export.');

    fetch('/ocr/export/pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(prepareDataForExport())
    })
    .then(res => res.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'ocr_data.pdf';
        a.click();
        a.remove();
    });
});

// Excel
document.getElementById('downloadExcel').addEventListener('click', () => {
    if (!editableExtractedData) return alert('No data to export.');

    fetch('/ocr/export/excel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(prepareDataForExport())
    })
    .then(res => res.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'ocr_data.xlsx';
        a.click();
        a.remove();
    });
});

// CSV
document.getElementById('downloadCSV').addEventListener('click', () => {
    if (!editableExtractedData) return alert('No data to export.');

    fetch('/ocr/export/csv', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(prepareDataForExport())
    })
    .then(res => res.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'ocr_data.csv';
        a.click();
        a.remove();
    });
});

// JSON (handled client-side)
document.getElementById('downloadJSON').addEventListener('click', () => {
    if (!editableExtractedData) return alert('No data to export.');

    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(prepareDataForExport(), null, 2));
    const a = document.createElement('a');
    a.href = dataStr;
    a.download = 'ocr_data.json';
    a.click();
    a.remove();
});

function exportCSV() {
    const data = prepareDataForExport();
    if (!data.extracted_data) return alert('No data to export.');

    let csv = 'Field,Value\n';

    // Flatten extracted data
    Object.entries(data.extracted_data).forEach(([key, value]) => {
        if (typeof value === 'object') {
            csv += `"${key}","${JSON.stringify(value)}"\n`;
        } else {
            csv += `"${key}","${value}"\n`;
        }
    });

    // Flatten verification
    if (data.verification) {
        csv += '\nVerification,,\n';
        csv += 'Check,Passed/Score\n';
        if (data.verification.checks) {
            Object.entries(data.verification.checks).forEach(([check, val]) => {
                csv += `"${check}","${val.passed ? '✅' : '❌'} / ${val.score || 0}"\n`;
            });
        }
        csv += `"Overall Score","${data.verification.overall_score || 0}"\n`;
        csv += `"Authentic","${data.verification.is_authentic ? 'Yes' : 'No'}"\n`;
        csv += `"Confidence Level","${data.verification.confidence_level || 'low'}"\n`;
    }

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = 'ocr_data.csv';
    a.click();
    URL.revokeObjectURL(url);
}
 function exportPDF() {
    const data = prepareDataForExport();
    if (!data.extracted_data) return alert('No data to export.');

    const doc = new jsPDF(); // or your render_pdf_inline

    let y = 10;

    doc.setFontSize(12);
    doc.text('=== Extracted Data ===', 10, y); y += 10;

    Object.entries(data.extracted_data).forEach(([key, value]) => {
        const text = `${key}: ${typeof value === 'object' ? JSON.stringify(value) : value}`;
        y += 6;
        doc.text(text, 10, y);
        if (y > 280) { doc.addPage(); y = 10; }
    });

    if (data.verification) {
        y += 10;
        doc.text('=== Verification ===', 10, y); y += 10;
        doc.text(`Overall Score: ${data.verification.overall_score || 0}`, 10, y); y += 6;
        doc.text(`Authentic: ${data.verification.is_authentic ? 'Yes' : 'No'}`, 10, y); y += 6;
        doc.text(`Confidence: ${data.verification.confidence_level || 'low'}`, 10, y); y += 6;

        if (data.verification.checks) {
            Object.entries(data.verification.checks).forEach(([check, val]) => {
                const text = `${check}: ${val.passed ? '✅' : '❌'} / ${val.score || 0}`;
                y += 6;
                doc.text(text, 10, y);
                if (y > 280) { doc.addPage(); y = 10; }
            });
        }
    }

    doc.save('ocr_data.pdf');
}

function applyEdits() {
    const fields = editDataForm.querySelectorAll('[data-path]');
    fields.forEach(field => {
        setValueByPath(editableExtractedData, field.dataset.path, field.value);
    });
}
function createInput(path, label, value) {
    const div = document.createElement('div');
    div.className = 'mb-3';
    div.innerHTML = `
        <label class="form-label">${label}</label>
        <input type="text" class="form-control" data-path="${path}" value="${escapeHtml(value)}">
    `;
    editDataForm.appendChild(div);
}

function createTextarea(path, label, value) {
    const div = document.createElement('div');
    div.className = 'mb-3';
    div.innerHTML = `
        <label class="form-label">${label}</label>
        <textarea class="form-control" rows="4" data-path="${path}">${escapeHtml(value)}</textarea>
    `;
    editDataForm.appendChild(div);
}

function setValueByPath(obj, path, value) {
    const keys = path.split('.');
    let ref = obj;
    for (let i = 0; i < keys.length - 1; i++) {
        ref = ref[keys[i]];
    }
    ref[keys[keys.length - 1]] = value;
}

function shouldSkipEditField(key, value) {
    return (
        value === null ||
        typeof value === 'object' ||
        ['_id', 'user_id', 'filename', 'doc_type', 'success', 'message', 'timestamp', 'verification', 'tables', 'images'].includes(key)
    );
}

function escapeHtml(text) {
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}
// ADD THESE NEW FUNCTIONS:

function showNotification(message, type = 'success') {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.style.cssText = 'position: fixed; top: 80px; right: 20px; z-index: 9999; min-width: 300px;';
    alert.innerHTML = `
        <i class="fas fa-check-circle"></i> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alert);

    setTimeout(() => {
        alert.remove();
    }, 3000);
}

function saveToBackend() {
    if (!currentRecordId) return;

    fetch(`/ocr/update/${currentRecordId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
            extracted_data: editableExtractedData,
            doc_type: editableDocType
        })
    })
    .then(res => res.json())
    .then(data => {
        console.log('Saved to backend:', data);
    })
    .catch(err => {
        console.error('Failed to save to backend:', err);
    });
}

console.log('✓ Dashboard initialized successfully');  // <-- FIX: Added the checkmark
});