// ======================
// Global State
// ======================



// ======================
// API Helper
// ======================
function api(action, data = {}, cb) {
    $.ajax({
        url: 'api.php?action=' + action,
        method: 'POST',
        data: JSON.stringify(data),
        contentType: 'application/json',
        success: cb
    });
}



// ======================
// Render Functions
// ======================

function renderSection(id, title) {
    return `
        <section class="theme">
            <h2>${title}</h2>
            <div class="image-grid" id="${id}">
            </div>
        </section>
    `;
}

function renderFigure(i) {
    return `
        <figure class="image-card">
            <img src="${i.imagename}" loading="lazy">

            <figcaption class="overlay">
                <h3>${i.viewed} · ${i.views} views · ${i.likeit} likes</h3>
                <p>${i.imagename}</p>
            </figcaption>
        </figure>    
    `;
}


// ======================
// Load Data
// ======================
function loadImageList() {
    api('webGetImageList', {}, res => {
        $('#ImageGallery').empty();
        $('#ImageGallery').append(renderSection('s_last', 'Last displayed'));
        res.lastViewed.forEach(i => {
            $('#s_last').append(renderFigure(i));
        });
        let section_id = null;
        res.liked.forEach(i => {
            if(section_id != i.likeit) {
                section_id = i.likeit;
                $('#ImageGallery').append(renderSection('s_' + section_id, 'Likes: ' + section_id));

            }
            $('#s_' + section_id).append(renderFigure(i));
        });

    });
}











// ======================
// Init
// ======================
$(document).ready(loadImageList);
