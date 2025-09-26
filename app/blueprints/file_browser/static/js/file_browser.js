// Browser globals
let editor = null;
let originalContent = '';
let hasUnsavedChanges = false;
let currentFile = null;
let pendingNavigation = null;
let unsavedChangesModal = null;

document.addEventListener('DOMContentLoaded', function() {
    unsavedChangesModal = new bootstrap.Modal(document.getElementById('unsavedChangesModal'));
    
    document.getElementById('zoomSlider').addEventListener('input', function() {
        updateImageZoom(this.value);
    });

    window.addEventListener('beforeunload', function(e) {
        if (hasUnsavedChanges) {
            e.preventDefault();
            e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
            return e.returnValue;
        }
    });
});

function yamlLintEditor(text) {
    try {
        jsyaml.load(text);
        return [];
    } catch (e) {
        return e.mark ? [{
            from: CodeMirror.Pos(e.mark.line, e.mark.column),
            to: CodeMirror.Pos(e.mark.line, e.mark.column + 1),
            message: e.message,
            severity: 'error'
        }] : [];
    }
}

function navigateToPath(path) {
    if (hasUnsavedChanges) {
        pendingNavigation = path;
        showUnsavedModal();
    } else {
        window.location.href = updateUrl(path);
    }
}

function selectFile(filepath, filename, filetype, filesize, theme) {
    if (hasUnsavedChanges) {
        pendingNavigation = () => performFileSelection(filepath, filename, filetype, filesize, theme);
        showUnsavedModal();
    } else {
        performFileSelection(filepath, filename, filetype, filesize, theme);
    }
}

function showUnsavedModal() {
    document.getElementById('modalFileName').textContent = currentFile?.filename || 'Unknown file';
    unsavedChangesModal.show();
}

function updateUrl(path) {
    const url = new URL(window.location);
    url.searchParams.set('path', path);
    return url.toString();
}

function performFileSelection(filepath, filename, filetype, filesize, theme, event) {
    document.querySelectorAll('.file-item').forEach(item => item.classList.remove('selected'));
    event?.currentTarget.classList.add('selected');

    currentFile = { filepath, filename, filetype, filesize };
    hideAllInterfaces();

    const fileExtension = filename.includes(".") ? filename.split('.').pop().toLowerCase() : "";
    // TODO: Move this to a list injected by flask context provider?
    if (["png","jpg","jpeg","gif","bmp","svg","webp"].includes(fileExtension)) {
        showImageViewer(filepath, filename);
    } else {
        showEditor(filepath, filename, getModeInfo(filename, fileExtension), theme);
    }
}

function hideAllInterfaces() {
    document.getElementById('noFileSelected').style.display = 'none';
    document.getElementById('editorInterface').style.display = 'none';
    document.getElementById('imageInterface').style.display = 'none';
}

function getModeInfo(filename, fileExtension) {
    const specialCases = {
        "dockerfile": { mode: "dockerfile", mime: "text/x-dockerfile" },
        "todo": { mode: "gfm", mime: "text/x-markdown" },
        ".env": { mode: "properties", mime: "text/x-properties" },
        "env": { mode: "properties", mime: "text/x-properties" },
        "makefile": { mode: "makefile", mime: "text/x-makefile" },
        "procfile": { mode: "shell", mime: "text/x-sh" }
    };

    return specialCases[filename.toLowerCase()] ||
           CodeMirror.findModeByFileName(filename) ||
           CodeMirror.findModeByExtension(fileExtension) ||
           { mode: "null", mime: "text/plain" };
}

function showImageViewer(filepath, filename) {
    document.getElementById('imageInterface').style.display = 'flex';
    document.getElementById('currentImageName').textContent = filename;
    
    const img = document.getElementById('imageDisplay');
    img.src = `/files/file/content?path=${encodeURIComponent(filepath)}`;
    img.onload = () => {
        document.getElementById('imageDimensions').textContent = `${img.naturalWidth} × ${img.naturalHeight}px`;
        resetImageZoom();
    };
}


function showEditor(filepath, filename, modeInfo, theme) {
    document.getElementById('editorInterface').style.display = 'flex';
    document.getElementById('currentFileName').textContent = filename;
    document.getElementById('fileTypeIndicator').textContent = modeInfo.mode;

    fetch(`/files/file/content?path=${encodeURIComponent(filepath)}`)
        .then(response => response.text())
        .then(content => {
            initializeEditor(content, modeInfo, theme);
            originalContent = content;
            hasUnsavedChanges = false;
            updateSaveStatus();
        })
        .catch(error => {
            console.error('Error loading file:', error);
            alert('Error loading file: ' + error.message);
        });
}

function loadCodeMirrorMode(mode, callback) {
    console.log(`Loading CodeMirror with ${mode}`);
    if (CodeMirror.modes.hasOwnProperty(mode)) {
        callback();
        return;
    }

    const script = document.createElement('script');
    script.src = `/static/js/codemirror/5.65.16/mode/${mode}/${mode}.min.js`;
    script.onload = callback;
    script.onerror = () => {
        console.error(`Failed to load CodeMirror mode: ${mode}`);
        callback();
    };
    document.head.appendChild(script);
}

function initializeEditor(content, modeInfo, theme) {
    console.log(`Initializing Editor - ${content}, ${theme}`)
    const container = document.getElementById('editorContainer');

    if (editor) {
        editor.toTextArea();
        editor = null;
    }

    container.innerHTML = '';
    const textarea = document.createElement('textarea');
    textarea.value = content;
    container.appendChild(textarea);

    loadCodeMirrorMode(modeInfo.mode, () => {
        const config = {
            mode: modeInfo.mime || modeInfo.mode,
            theme: theme,
            lineNumbers: true,
            lineWrapping: true,
            autoCloseBrackets: true,
            matchBrackets: true,
            styleActiveLine: true,
            gutters: ["CodeMirror-linenumbers", "CodeMirror-foldgutter"],
            foldGutter: true,
            indentUnit: 2,
            tabSize: 2,
            readOnly: false,
            extraKeys: {
                "Ctrl-S": saveCurrentFile,
                "Cmd-S": saveCurrentFile,
                "Tab": cm => cm.somethingSelected() 
                    ? cm.indentSelection("add") 
                    : cm.replaceSelection("  ", "end")
            }
        };

        if (modeInfo.mode === 'yaml') {
            config.gutters.push("CodeMirror-lint-markers");
            config.lint = { getAnnotations: yamlLintEditor, async: false };
        }

        editor = CodeMirror.fromTextArea(textarea, config);
        
        // Update cursor position on cursor activity
        editor.on('cursorActivity', updateCursorPosition);
        
        editor.on('change', () => {
            hasUnsavedChanges = (editor.getValue() !== originalContent);
            updateSaveStatus();
        });
        
        // Initialize cursor position
        updateCursorPosition();
    });
}

function updateCursorPosition() {
    if (!editor) return;
    const cursor = editor.getCursor();
    const line = cursor.line + 1;
    const col = cursor.ch + 1;
    document.getElementById('cursorPosition').textContent = `Ln ${line}, Col ${col}`;
}

function updateSaveStatus() {
    const saveStatusText = document.getElementById('saveStatusText');
    const unsavedIcon = document.getElementById('unsavedIcon');
    const savedIcon = document.getElementById('savedIcon');
    const saveButton = document.getElementById('saveButton');
    
    if (hasUnsavedChanges) {
        saveStatusText.textContent = 'Unsaved changes';
        unsavedIcon.style.display = 'inline';
        savedIcon.style.display = 'none';
        saveButton.disabled = false;
    } else {
        saveStatusText.textContent = 'Saved';
        unsavedIcon.style.display = 'none';
        savedIcon.style.display = 'inline';
        saveButton.disabled = true;
    }
}

function saveCurrentFile() {
    if (!currentFile || !editor || !hasUnsavedChanges) return;

    const formData = new FormData();
    formData.append('filepath', currentFile.filepath);
    formData.append('filename', currentFile.filename);
    formData.append('filecontent', editor.getValue());

    fetch('/files/file/save', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data?.success) {
            originalContent = editor.getValue();
            hasUnsavedChanges = false;
            updateSaveStatus();
            showSaveConfirmation();
        } else {
            alert('Error saving file: ' + (data?.message || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error saving file:', error);
        alert('Error saving file: ' + error.message);
    });
}

function showSaveConfirmation() {
    const saveStatusText = document.getElementById('saveStatusText');
    const originalText = saveStatusText.textContent;
    
    saveStatusText.textContent = 'Changes saved';
    setTimeout(() => {
        if (!hasUnsavedChanges) {
            saveStatusText.textContent = originalText;
        }
    }, 2000);
}

function saveAndProceed() {
    if (!currentFile || !editor || !hasUnsavedChanges) return;

    const formData = new FormData();
    formData.append('filepath', currentFile.filepath);
    formData.append('filename', currentFile.filename);
    formData.append('filecontent', editor.getValue());

    fetch('/files/file/save', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data?.success) {
            originalContent = editor.getValue();
            hasUnsavedChanges = false;
            updateSaveStatus();
            unsavedChangesModal.hide();
            executePendingNavigation();
        } else {
            alert('Error saving file: ' + (data?.message || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error saving file:', error);
        alert('Error saving file: ' + error.message);
    });
}

function discardChanges() {
    hasUnsavedChanges = false;
    updateSaveStatus();
    unsavedChangesModal.hide();
    executePendingNavigation();
}

function executePendingNavigation() {
    if (pendingNavigation) {
        if (typeof pendingNavigation === 'function') {
            pendingNavigation();
        } else {
            window.location.href = updateUrl(pendingNavigation);
        }
        pendingNavigation = null;
    }
}

function resetImageZoom() {
    document.getElementById('zoomSlider').value = 100;
    updateImageZoom(100);
}

function updateImageZoom(value) {
    const img = document.getElementById('imageDisplay');
    img.style.width = value + '%';
    img.style.height = 'auto';
    document.getElementById('zoomValue').textContent = value + '%';
}