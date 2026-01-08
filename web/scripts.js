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
            <div class="actions">
                <button class="imgView"  title="Ansehen">🖥️</button>
                <button class="imgLup"   title="Like +">👍</button>
                <button class="imgLdown" title="Like -">👎</button>
                <button class="imgDel"   title="Löschen">🗑</button>
            </div>
            <figcaption class="overlay">
                <div class="overlay-content">
                    <h3>${i.viewed} · ${i.views} views · ${i.likeit} likes</h3>
                    <p>${i.imagename}</p>
                </div>
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
                if(section_id < 0)$('#s_' + section_id).parent().addClass('theme-red');
            }
            $('#s_' + section_id).append(renderFigure(i));
        });

    });
}



// ======================
// Action: Web - Update Database
// ======================
$('#btnControlUpdate').on('click', function(e) {
    e.preventDefault();
    e.stopPropagation();
    showLoader("Updating Database");
    api('webUpdateDatabase', {}, res => {
        if(res.new.length > 10) html = "<strong>New images</strong> " + res.new.length;
        else html = "<strong>New images:</strong><br>" + res.new.join('<br>');
        html += "<br><br>";
        if(res.delted.length > 10) html += "<strong>Delted images</strong> " + res.delted.length;
        else html += "<strong>Delted images:</strong><br>" + res.delted.join('<br>');
        unlockLoader(html);
    });
});

// ======================
// Action: Web - Random Image
// ======================
$('#btnControlRandom').on('click', function(e) {
    e.preventDefault();
    e.stopPropagation();
    api('webGetRandomImage', {}, res => {
        lightboxShowImage(res.imagename);
    });
});

// ======================
// Action: Inky - Show Next Image
// ======================
$('#btnControlInkyNext').on('click', function(e) {
    e.preventDefault();
    e.stopPropagation();
    showLoader('Requested Inky to display next random image.');
    api('webSendToInky', { action: 'next'}, res => {
        if(res == "OK")
            hideLoader();
        else
            unlockLoader(res);
    });
});

// ======================
// Action: Inky - Clear Display
// ======================
$('#btnControlInkyClean').on('click', function(e) {
    e.preventDefault();
    e.stopPropagation();
    showLoader('Clearing Inky Display.');
    api('webSendToInky', { action: 'clear'}, res => {
        if(res == "OK")
            hideLoader();
        else
            unlockLoader(res);
    });
});

// ======================
// Action: Inky - Show URL
// ======================
$('#btnControlInkyDisplay').on('click', function(e) {
    e.preventDefault();
    e.stopPropagation();
    const i = $('#btnControlInkyUrl').val();
    showLoader('Image ' + i + ' send to Inky.');
    api('webSendToInky', { action: 'show', url: i}, res => {
        if(res == "OK")
            hideLoader();
        else
            unlockLoader(res);
    });
});

// ======================
// Image-Action: Inky - Show this Image
// ======================
$(document).on('click', '.imgView', function(e) {
    e.preventDefault();
    e.stopPropagation();
    const f = $(this).closest('figure');
    const i = f.find('img').attr('src');
    showLoader('Image ' + i + ' send to Inky.');
    api('webSendToInky', { action: 'show', url: i}, res => {
        if(res == "OK")
            hideLoader();
        else
            unlockLoader(res);
    });
});








// ======================
// Loader
// ======================
let loaderLocked = false;
function showLoader(text) {
    loaderLocked = true;
    $('#loader .loader-text').html(text);
    $('#loader .spinner').show();
    $('#loader').addClass('visible');
}
function hideLoader() {
    $('#loader').removeClass('visible');
}
function unlockLoader(text) {
    loaderLocked = false;
    $('#loader .loader-text').html(text);
    $('#loader .spinner').hide();
    $('#loader').addClass('visible');
}
$('#loader').on('click', function(e) {
    e.preventDefault();
    e.stopPropagation();
    if(!loaderLocked)
        hideLoader();
});


// ======================
// Lightbox
// ======================
$(document).on('click', '.image-card img', function(e) {
    e.preventDefault();
    e.stopPropagation();
    lightboxShowImage($(this).attr('src'));
});
$('#lightbox').on('click', function(e) {
    e.preventDefault();
    e.stopPropagation();
    $('#lightbox').removeClass('visible');
});
function lightboxShowImage(url) {
    $('#lightbox-img').attr('src', '');
    $('#lightbox-img').attr('src', url);
    $('#lightbox').addClass('visible');
}

// ======================
// Scroll to top
// ======================
const scrollBtn = document.getElementById('scrollTopBtn');

window.addEventListener('scroll', () => {
    scrollBtn.classList.toggle('visible', window.scrollY > 150);
});

scrollBtn.addEventListener('click', () => {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
});

// ======================
// Init
// ======================
$(document).ready(loadImageList);
