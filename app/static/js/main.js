$(document).ready(function() {
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
    let $chunkContainer = $('#chunk-container');
    let $sceneContainer = $('#scene-container');
    let $sceneContainerLabel = $('#scene-container-label');
    let $leftNav = $('#left-nav');
    
    function toggleActivateChunk($chunk) {
        // deactivate
        if ($chunk.hasClass('active')) {
            $chunk.removeClass('active');
            $sceneContainer.removeClass('show');
            $leftNav.width('auto');
            $chunkContainer.width('auto');
        // activate
        } else {
            $('.card.chunk.active').removeClass('active');
            $chunk.addClass('active');
            $sceneContainer.addClass('show');
            $sceneContainer.data('chunkId', $chunk.data('chunkId'));
            $chunkContainer.width(315);
            console.log('$chunkContainer', $chunkContainer);
            $sceneContainerLabel.text($chunk.find('.chunk-title').text());
            $leftNav.animate({
                width: 0
            }, 500);
        }
    }

    if ($chunks.length) {
        // toggleActivateChunk($chunks.eq(0));
    }

    $('.card.chunk').click(function(evt) {
        toggleActivateChunk($(this));
    });

    $('#scene-container-close').click(function(evt) {
        evt.preventDefault();
        toggleActivateChunk($('.card.chunk.active'));
    });

    $('.chunk-generate-image').click(function(evt) {
        evt.preventDefault();
        const chunkId = $(this).data('chunk-id');
        alert(chunkId);
    });

    $('.card.chunk .chunk-expand').click(function(evt) {
        evt.preventDefault();
        const card = $(this).closest('.card'); // Get the parent .card of the clicked .expand button

        function animateCard(card) {
            card.addClass('expanded');
            card.animate({
                width: "100%"
            }, 500, function() {
                // Once the animation is complete
                var cardPosition = $('.card.chunk.expanded').offset().top;
                $('html, body').animate({
                    scrollTop: cardPosition
                }, 500);
            });
        }

        if (card.hasClass('expanded')) {
            // If the card is already expanded, collapse it
            console.log('go');
            card.animate({
                width: defaultCardWidth,
            }, 500, function() {
                console.log('removing class for card', card);
                $(this).removeClass('expanded')
            });
        } else {
            // If a different card is already expanded, collapse it
            const existingExpandedCard = $('.card.chunk.expanded')
            if (existingExpandedCard.length ) {
                $('.card.chunk.expanded').animate({
                    width: defaultCardWidth,
                }, 500, function() {
                    $(this).removeClass('expanded');
                    animateCard(card);
                });
            } else {
                animateCard(card);
            }

        }
    });

    /*
     * Generate Scene
    */
    $('#form-generate-scene').submit(function(evt) {
        evt.preventDefault();
        // Get the form action (URL to which the form would post)
        var postUrl = $(this).attr("action");

        // Serialize form data for the post request
        var data = $(this).serializeObject();
        data['chunk_id'] = $sceneContainer.data('chunkId');
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
                    alert(error);
                } else {
                    // console.log('polling for task #', response.task_id)
                    $('#scene-generation-progress').text('...')
                }
        }}).fail(function(jqXHR, textStatus, errorThrown) {
            // Handle error during the request
            console.error("Request failed: " + textStatus + ". " + errorThrown);
            var errorMsg = "Request failed: " + textStatus;
            if (errorThrown) {
                errorMsg += ". " + errorThrown;
            }
            alert(errorMsg)
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
