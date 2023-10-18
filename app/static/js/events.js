function refreshImagesFromScene(sceneId) {
    console.log('refreshImagesFromScene', sceneId);
}

function getGenerateImageUpdates(
    taskId
) {
    console.log('[getGenerateImageUpdates]', taskId);
    const url = `ws://localhost:8004/ws/${taskId}`;
    const socket = new ReconnectingWebSocket(url);
    socket.debug = true

    socket.onopen = ()=>{
        // $('#websocket-status').removeClass('reconnecting').addClass('open')
        console.log('websocket open')
    }

    socket.onclose = ()=>{
        // $('#websocket-status').removeClass('open').addClass('reconnecting')
        console.log('websocket closed')
    }

    socket.onmessage = async (msg) => {
        let data = {};
        try {
            data = msg.data && JSON.parse(msg.data);
            console.log('data', data);
        } catch (err) {
            console.error('websocket msg is not JSON');
            console.log('websocket message', msg);
        }

        if (data.task_results.error && data.task_results.error.length) {
            console.error(`Sorry, there was an error generating images: ${data.task_results.error}`);
            $('#generate-scene-image-error').show().find('.message').text(data.task_results.error);
        }
        else if (data.task_results && data.task_results.type == 'scene_image_generate' && data.task_results.content) {
            console.log('scene_image_generate contents');
            if (data.completed) {
                console.log("SCENE IMAGE GENERATION FINISHED");
                refreshImagesFromScene(data.task_results.scene_id);
            }
        }
    }
}

function getGenerateSceneUpdates(
    taskId,
    $generateSceneContent,
    $generateSceneError,
    $generateSceneLoader,
    $generateSceneButton,
) {

    console.log('[getGenerateSceneUpdates] taskId=', taskId);

    const url = `ws://localhost:8004/ws/${taskId}`;

    const socket = new ReconnectingWebSocket(url);

    $('#generate-scene-image-error').hide();

    socket.debug = true

    socket.onopen = ()=>{
        // $('#websocket-status').removeClass('reconnecting').addClass('open')
        console.log('websocket open')
    }

    socket.onclose = ()=>{
        // $('#websocket-status').removeClass('open').addClass('reconnecting')
        console.log('websocket closed')
    }

    let sceneGenerateBlock = false;
    let messageQueue = [];
    let sceneGenerateContent = '';

    $generateSceneContent.html('');

    var addTextByDelay = function(text, elem, delay, finishCallback) {
        if (text.length > 0) {
            // Append first character 
            elem.append(text[0]);
            setTimeout(function () {
                // Slice text by 1 character and call function again                
                addTextByDelay(text.slice(1), elem, delay, finishCallback);
            }, delay);
        } else {
            finishCallback && finishCallback();
        }
    }

    async function processNextMessage() {
        console.log('processNextMessage, messageQueue is', messageQueue);
        if (messageQueue.length > 0) {
            sceneGenerateBlock = true;

            const data = messageQueue.shift();
            const content = data.task_results.content;
            const lengthDiff = sceneGenerateContent.length - content.length;
            const newContent = content.slice(lengthDiff);

            console.log('content', content);
            console.log('lengthDiff', lengthDiff)
            console.log('newContent', newContent)

            // TODO: we may be able to smooth the print effect by increasing 0 here
            if (newContent.length > 0 && Math.abs(lengthDiff) > 0) {
                await new Promise(resolve => {
                    addTextByDelay(newContent, $generateSceneContent, 1, () => {
                        sceneGenerateBlock = false;
                        resolve(); // Resolve the promise to continue processing the next message
                    });
                });
            } else {
                sceneGenerateBlock = false;
            }

            sceneGenerateContent = data.task_results.content;

            // Process the next message in the queue
            await processNextMessage();
        }
    }


    socket.onmessage = async (msg) => {
        let data = {};
        console.log('websocket message', msg);
        try {
            data = msg.data && JSON.parse(msg.data);

            // Scene Generation Updates
            if (data.task_results && data.task_results.type == 'scene_generate' && data.task_results.content) {
                messageQueue.push(data);
                if (!sceneGenerateBlock) {
                    await processNextMessage();
                }
                if (data.completed) {
                    console.log('SCENE GENERATION FINISHED');

                    // subscribe to image-generation task
                    sceneImageTaskId = data.task_results.scene_image_task_id;
                    console.log('calling getGenerateImageDetails', sceneImageTaskId);
                    getGenerateImageUpdates(sceneImageTaskId);


                    $generateSceneLoader.hide();
                    $generateSceneButton.prop('disabled', false);
                    refreshScenesFromChunk(chunkId)
                }
            }
            
        } catch (err) {
            console.log('websocket is not JSON');
        }
    }

}