let $leftNav;
let $chunkContainer;
let $generateSceneContainer;
let $generateSceneContainerLabel;
let $generateSceneContent;
let $generateSceneError;
let $generateSceneLoader;
let $generateSceneButton;
let $currentScenesLoader;
let $currentScenesError;
let $sceneImagesLoader;
let $sceneImagesError;

document.addEventListener('alpine:init', () => {
    // init Alpine data
    Alpine.data('recentScenes', () => ({
        scenes: [],
    }));

    Alpine.data('currentScenes', () => ({
        scenes: [],
    }));

    Alpine.data('currentSceneImages', () => ({
        sceneImages: [],
    }));

    Alpine.data('promptTemplates', () => ({
        templates: [],
    }));
});

function refreshRecentScenes() {
    $.get('/scenes/recent', function(data){
        console.log('recentScenes', data);
        // refresh the Alpine data
        let event = new CustomEvent("recent-scenes-load", {
            detail: {
                scenes: data
            }
        });
        window.dispatchEvent(event);
    });
}

function refreshScenesFromChunk(chunkId) {
    console.log('refreshScenes from', chunkId);
    $.get(`/scenes/from_chunk/${chunkId}`, function(data) {
        console.log('data', data);
        // refresh the Alpine data
        let event = new CustomEvent("scenes-load", {
            detail: {
                scenes: data
            }
        });
        window.dispatchEvent(event);
        $currentScenesError.hide();
    }).fail(function(jqXHR, textStatus, errorThrown) {
        console.error("refreshScenesFromChunk failed: " + textStatus + ". " + errorThrown);
        $currentScenesError.show().find('.message').text(errorThrown);
    }).always(function() {
        $currentScenesLoader.hide();
    });
}

function refreshImagesFromChunk(chunkId) {
    console.log('refreshImagesFromChunk', chunkId);
    $sceneImagesLoader.show();
    $.get(`/images/from_chunk/${chunkId}`, function(data) {
        console.log('[refreshImagesFromChunk] data', data);

        // refresh the Alpine data
        let event = new CustomEvent("scene-images-load", {
            detail: {
                sceneImages: data
            }
        });
        window.dispatchEvent(event);

        $sceneImagesError.hide();
    }).fail(function(jqXHR, textStatus, errorThrown) {
        $sceneImagesError.show().find('.message').text(errorThrown);
    }).always(function() {
        $sceneImagesLoader.hide();
    });
}

function refreshPromptTemplates() {
    console.log('refreshpromptTemplates');
    $('#create-prompt-template-loader').show();
    $.get(`/prompt_templates`, function(data) {
        console.log('data', data);
        // refresh the Alpine data
        let event = new CustomEvent("prompt-templates-load", {
            detail: {
                templates: data
            }
        });
        window.dispatchEvent(event);
    }).fail(function(jqXHR, textStatus, errorThrown) {
        console.error("refreshPromptTemplates failed: " + textStatus + ". " + errorThrown);
        $currentScenesError.show().find('.message').text(`There was an error loading prompt templates: ${errorThrown}`);
    }).always(function() {
        $('#create-prompt-template-loader').hide();
    });
}

function checkIfChunkShouldOpen() {
    var match = window.location.pathname.match(/\/books\/(\d+)/);
    var hash = window.location.hash.match(/#chunk-(\d+)/);

    if (match && hash) {
        var chunkId = hash[1];
        console.log("Chunk ID:", `#card-chunk-${chunkId}`);
        let $chunkCard = $(`#card-chunk-${chunkId}`);
        toggleActivateChunk($chunkCard)
    }
}

function toggleActivateChunk($chunk) {
    // deactivate
    if ($chunk.hasClass('active')) {
        $chunk.removeClass('active');
        $generateSceneContainer.removeClass('show');
        $leftNav.width('auto');
        $chunkContainer.width('auto');
    // activate
    } else {

        $('.card.chunk.active').removeClass('active');
        $chunk.addClass('active');
        $generateSceneContainer.addClass('show');
        $generateSceneContainer.data('chunkId', $chunk.data('chunkId'));
        $chunkContainer.width(315);
        console.log('$chunkContainer', $chunkContainer);
        $generateSceneContainerLabel.text($chunk.find('.chunk-title').text());
        

        $leftNav.animate({
            width: 0
        }, 500, function(){
            $('html, body').animate({
                scrollTop: $chunk.position().top - 50
            }, 500);
        });

        $currentScenesLoader.show();

        
        const chunkId = $chunk.data('chunkId');
        refreshScenesFromChunk(chunkId);
        refreshImagesFromChunk(chunkId);
    }
}

$(document).ready(function() {
    $leftNav = $('#left-nav');
    $chunkContainer = $('#chunk-container');
    $generateSceneContainer = $('#generate-scene-container');
    $generateSceneContainerLabel = $('#generate-scene-container-label');
    $generateSceneContent = $('#generate-scene-content');
    $generateSceneError = $('#generate-scene-error');
    $generateSceneLoader = $('#generate-scene-loader');
    $generateSceneButton = $('#generate-scene-btn');
    $currentScenesLoader = $('#current-scenes-loader');
    $currentScenesError = $('#current-scenes-error');
    $sceneImagesLoader = $('#scene-images-loader');
    $sceneImagesError = $('#scene-images-error');

    refreshRecentScenes();
    refreshPromptTemplates();
    checkIfChunkShouldOpen();

    // for serializing form data into JSON
    $.fn.serializeObject = function() {
        var o = {};
        var a = this.serializeArray();
        $.each(a, function() {
            if (o[this.name]) {
                if (!o[this.name].push) {
                    o[this.name] = [o[this.name]];
                }
                o[this.name].push(this.value || '');
            } else {
                o[this.name] = this.value || '';
            }
        });
        return o;
    };

    /*
    * ALERTS
    */
    $("#errorAlert .close").click(function(evt) {
        evt.preventDefault();
        $("#errorAlert").hide();
    });

    /*
     * CONFIG
    */
    $('#config-nav-toggle').click(function(evt) {
        let $container = $('#config-nav-container');
        let $nav = $('#config-nav');
        // already expanded
        if ($container.hasClass('expanded')) {
            $nav.animate({
                height: 0
            }, 500, function() {
                $container.removeClass('expanded');
            });
            $container.removeClass('expanded');
        } else {
            let newHeight = $(window).height() - 50;
            console.log('newHeight', newHeight);
            $nav.animate({
                height: newHeight
            }, 500, function() {
                $container.addClass('expanded');
            });
        }
    });
    $('#configSaveChunkSize').click(function(evt) {
        evt.preventDefault();
        alert('Not Implemented Yet');
    });

    /*
     * PROMPT TEMPLATES
    */
   $('#create-prompt-template-form').submit(function(evt) {
        evt.preventDefault();

        $('#generate-scene-success').hide();
        $('#create-prompt-template-loader').show();
        $('#create-prompt-template-btn').prop('disabled', true);

        // Get the form action (URL to which the form would post)
        var postUrl = $(this).attr("action");

        // Serialize form data for the post request
        var data = $(this).serializeObject();
        console.log('data', data);

        $.ajax({
            type: "POST",
            url: postUrl,
            dataType: "json",
            contentType: "application/json; charset=utf-8",
            data: JSON.stringify(data),
            success: function(response) {
                $('#create-prompt-template-error').hide();
                refreshPromptTemplates();
                $('#generate-scene-success').show();
            }
        }).fail(function(jqXHR, textStatus, errorThrown) {
            // Handle error during the request
            console.error("Request failed: ", jqXHR , textStatus + ". " + errorThrown);
            $('#generate-scene-success').hide();
            $('#create-prompt-template-error').show().find('.message').text(jqXHR.responseJSON.detail);
        }).always(function() {
            $('#create-prompt-template-loader').hide();
            $('#create-prompt-template-btn').prop('disabled', false);
        });
    });

    /*
     * CHUNKS
    */
    const defaultCardWidth = '17rem';
    let $chunks = $('.card.chunk');


    if ($chunks.length) {
        // toggleActivateChunk($chunks.eq(0));
    }

    $('.card.chunk').click(function(evt) {
        toggleActivateChunk($(this));
    });

    $('#generate-scene-container-close').click(function(evt) {
        evt.preventDefault();
        toggleActivateChunk($('.card.chunk.active'));
    });


    /*
     * Generate Scene
    */
    $('#generate-scene-form').submit(function(evt) {
        evt.preventDefault();

        let chunkId = $generateSceneContainer.data('chunkId');
        $generateSceneLoader.show();
        $generateSceneButton.prop('disabled', true);

        // collapse currently-active scenes
        $('.accordion-button').addClass('collapsed');
        $('.accordion-collapse.show').removeClass('show');

        // Get the form action (URL to which the form would post)
        var postUrl = $(this).attr("action");

        // Serialize form data for the post request
        var data = $(this).serializeObject();
        data['chunk_id'] = chunkId;
        console.log('data', data);

        $.ajax({
            type: "POST",
            url: postUrl,
            dataType: "json",
            contentType: "application/json; charset=utf-8",
            data: JSON.stringify(data),
            success: function(response) {
                console.log(response);
                getGenerateSceneUpdates(
                    response.task_id,
                    chunkId,
                    $generateSceneContent,
                    $generateSceneError,
                    $generateSceneLoader,
                    $generateSceneButton,
                );
                $generateSceneError.hide();
            }
        }).fail(function(jqXHR, textStatus, errorThrown) {
            // Handle error during the request
            $generateSceneError.show().find('.message').text(errorThrown);
            $generateSceneLoader.hide();
            $generateSceneButton.prop('disabled', false);
            console.error("Request failed: " + textStatus + ". " + errorThrown);
            var errorMsg = "Request failed: " + textStatus;
            if (errorThrown) {
                errorMsg += ". " + errorThrown;
            }
        }).always(function() {
        });
    });

    /*
     * BOOK IMPORT
    */
    $("#form_book_import").submit(function(evt) {
        // Prevent default form submission
        evt.preventDefault();

        // Get the form action (URL to which the form would post)
        var postUrl = $(this).attr("action");

        // Serialize form data for the post request
        var data = $(this).serializeObject();

        $(this).find(":input").prop("disabled", true);
        $("#loadingSpinner").show();

        console.log('data', data);

        $.ajax({
            type: "POST",
            url: postUrl,
            dataType: "json",
            contentType: "application/json; charset=utf-8",
            data: JSON.stringify(data),
            success: function(response) {
                console.log(response);

                if (response.error) {
                    $("#successAlert").hide();
                    $("#errorMessage").text(response.error);
                    $("#errorAlert").show();
                } else {
                    $("#errorAlert").hide();
                    $("#successMessage").text('Book imported successfully');
                    $("#successAlert").show();

                    window.location.reload()

                }
        }}).fail(function(jqXHR, textStatus, errorThrown) {
            // Handle error during the request
            console.error("Request failed: " + textStatus + ". " + errorThrown);
            var errorMsg = "Request failed: " + textStatus;
            if (errorThrown) {
                errorMsg += ". " + errorThrown;
            }
            $("#errorMessage").text(errorMsg);
            $("#errorAlert").show();
        }).always(function() {
            $("#form_book_import").find(":input").prop("disabled", false);
            $("#loadingSpinner").hide();
        });

    });
});
