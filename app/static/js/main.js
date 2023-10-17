
document.addEventListener('alpine:init', () => {
    // init Alpine data
    Alpine.data('currentScenes', () => ({
        scenes: [],
    }));
});

$(document).ready(function() {
    const $leftNav = $('#left-nav');
    const $chunkContainer = $('#chunk-container');
    const $generateSceneContainer = $('#generate-scene-container');
    const $generateSceneContainerLabel = $('#generate-scene-container-label');
    const $generateSceneContent = $('#generate_scene_content');
    const $generateSceneError = $('#generate-scene-error');
    const $generateSceneLoader = $('#generate-scene-loader');
    const $generateSceneButton = $('#generate-scene-btn');
    const $currentScenesLoader = $('#current-scenes-loader');
    const $currentScenesError = $('#current-scenes-error');

    function refreshScenesFromChunk(chunkId) {
        $.get(`/scenes_from_chunk/${chunkId}`, function(data) {
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
            $currentScenesError.show();
        }).always(function() {
            $currentScenesLoader.hide();
        });
    }

    function refreshImagesFromScene(sceneId) {
        console.log('refreshImagesFromScene', sceneId);
    }

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
     * CHUNKS
    */
    const defaultCardWidth = '17rem';
    let $chunks = $('.card.chunk');
    
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
        }
    }

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
    $('#form-generate-scene').submit(function(evt) {
        evt.preventDefault();

        $generateSceneLoader.show();
        $generateSceneButton.prop('disabled', true);
        // Get the form action (URL to which the form would post)
        var postUrl = $(this).attr("action");

        // Serialize form data for the post request
        var data = $(this).serializeObject();
        data['chunk_id'] = $generateSceneContainer.data('chunkId');
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
                    $generateSceneContent,
                    $generateSceneError,
                    $generateSceneLoader,
                    $generateSceneButton,
                );
                $generateSceneError.hide();
            }
        }).fail(function(jqXHR, textStatus, errorThrown) {
            // Handle error during the request
            $generateSceneError.show();
            console.error("Request failed: " + textStatus + ". " + errorThrown);
            var errorMsg = "Request failed: " + textStatus;
            if (errorThrown) {
                errorMsg += ". " + errorThrown;
            }
            alert(errorMsg)
        }).always(function() {
            // $sceneGenerationLoader.hide();
            // $('#scene-generate-btn').prop('disabled', true);
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
