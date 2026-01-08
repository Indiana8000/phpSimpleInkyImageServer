/**
 * Project: phpSimpleInkyImageServer
 * File:    script.js
 * Purpose: AJAX content handling
 */



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
        console.log(res);
        if(res['new'].length == 0 || res['new'].length > 10) html = "<strong>New images:</strong> " + res['new'].length;
        else html = "<strong>New images:</strong><br>" + res['new'].join('<br>');
        html += "<br><br>";
        if(res['deleted'].length == 0 || res['deleted'].length > 10) html += "<strong>Deleted images:</strong> " + res['deleted'].length;
        else html += "<strong>Delted images:</strong><br>" + res['deleted'].join('<br>');
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
        if(res == "OK") {
            loadImageList();
            hideLoader();
        } else
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
        if(res == "OK") {
            $('#btnControlInkyUrl').val('');
            hideLoader();
        } else
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
// Image-Action: Delete Image
// ======================
$(document).on('click', '.imgDel', function(e) {
    e.preventDefault();
    e.stopPropagation();
    const f = $(this).closest('figure');
    const i = f.find('img').attr('src');
    if(confirm("Delete Image?\n" + i))
        showLoader('Deleting file from Disk and Database:<br>' + i);
        api('webDeleteImage', { url: i}, res => {
            if(res == "OK") {
                $(f).remove();
                hideLoader();
            } else
                unlockLoader(res);
        });
});

// ======================
// Image-Action: Vote Image
// ======================
$(document).on('click', '.imgLup', function(e) {
    e.preventDefault();
    e.stopPropagation();
    const f = $(this).closest('figure');
    const i = f.find('img').attr('src');
    api('webVoteImage', { likeit: 1, url: i}, res => {
        if(res == "OK") {
            loadImageList();
        } else
            unlockLoader(res);
    });
});
$(document).on('click', '.imgLdown', function(e) {
    e.preventDefault();
    e.stopPropagation();
    const f = $(this).closest('figure');
    const i = f.find('img').attr('src');
    api('webVoteImage', { likeit: -1, url: i}, res => {
        if(res == "OK") {
            loadImageList();
        } else
            unlockLoader(res);
    });
});



// ======================
// Dialog: Loader
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
// Dialog: Lightbox
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
// Scroll to top Button
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
// Auto Complete
// ======================
let debounceTimer = null;

$('#btnControlInkyUrl').on('input', function(e) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
        searchPattern($('#btnControlInkyUrl').val().trim());
    }, 350);
})
$('#btnControlInkyUrl').on('focus', function(e) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
        searchPattern($('#btnControlInkyUrl').val().trim());
    }, 350);
})
$('#btnControlInkyUrl').on('blur', function(e) {
    clearTimeout(debounceTimer);
    hideList();
})
$('#btnControlInkyUrl').on('keydown', function(e) {
    if (e.key === 'Escape') {
        hideList();
        return;
    } else {
        return
    }
});

async function searchPattern(query) {
    if (!query || query.length < 2) {
        hideList();
        return;
    }

    api('searchFile', { pattern: query }, res => {
        renderList(res);
    });
}
function renderList(items) {
    if (!items.length) {
        hideList();
        return;
    }

    $('#autocomplete-list').html('');
    items.forEach((item, index) => {
        const li = document.createElement('li');
        li.textContent = item.imagename;

        li.addEventListener('mousedown', () => {
            window.scrollTo({top: 0, behavior: 'smooth'});
            $('#btnControlInkyUrl').val(item.imagename);
            lightboxShowImage(item.imagename);
            hideList();
        });

        $('#autocomplete-list').append(li);
    });

    $('#autocomplete-list').addClass('visible');
}
function hideList() {
    $('#autocomplete-list').removeClass('visible');
    $('#autocomplete-list').html('');
}



// ======================
// Init
// ======================
$(document).ready(loadImageList);
