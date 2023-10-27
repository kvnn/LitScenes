const currentHostname = window.location.hostname;
const currentPort = window.location.port;
let websocketUrl = `ws://${currentHostname}`;

if (currentPort && currentPort.length) {
    websocketUrl = `${websocketUrl}:${currentPort}`;
}

websocketUrl = `${websocketUrl}/ws`;

console.log('websocketUrl', websocketUrl);

function getGenerateImageUpdates(
    taskId
) {
    console.log('[getGenerateImageUpdates]', taskId);
    const url = `${websocketUrl}/${taskId}`;
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

        if (data.task_results && data.task_results.error && data.task_results.error.length) {
            console.error(`Sorry, there was an error generating images: ${data.task_results.error}`);
            $('#generate-scene-image-error').show().find('.message').text(data.task_results.error);
            $sceneImagesLoader.hide();
        } else if (data.completed) {
            console.log("SCENE IMAGE GENERATION FINISHED");
            refreshImagesFromChunk(data.task_results.chunk_id);
        }
    }
}

function getGenerateSceneUpdates(
    taskId,
    chunkId,
    $generateSceneContent,
    $generateSceneError,
    $generateSceneLoader,
    $generateSceneButton,
) {

    console.log('[getGenerateSceneUpdates] taskId=', taskId);

    const url = `${websocketUrl}/${taskId}`;

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
            if (newContent.length > 30 && Math.abs(lengthDiff) > 0) {
                await new Promise(resolve => {
                    addTextByDelay(newContent, $generateSceneContent, 1, () => {
                        sceneGenerateBlock = false;
                        resolve(); // Resolve the promise to continue processing the next message
                    });
                });
                sceneGenerateContent = data.task_results.content;
            } else {
                sceneGenerateBlock = false;
            }

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
            if (data.task_results && data.task_results.error && data.task_results.error.length) {
                $generateSceneError.show().find('.message').text(data.task_results.error);
                $generateSceneButton.prop('disabled', false);
                $generateSceneLoader.hide();
            } else if (data.task_results && data.task_results.type == 'scene_generate' && data.task_results.content) {
                messageQueue.push(data);
                if (!sceneGenerateBlock) {
                    await processNextMessage();
                }
                if (data.completed) {
                    console.log('SCENE GENERATION FINISHED');

                    $generateSceneContent.slideUp().html('').slideDown();

                    $generateSceneLoader.hide();
                    $generateSceneButton.prop('disabled', false);
                    refreshScenesFromChunk(chunkId);

                    // subscribe to image-generation task
                    sceneImageTaskId = data.task_results.scene_image_task_id;
                    console.log('calling getGenerateImageDetails', sceneImageTaskId);
                    $sceneImagesLoader.show();
                    getGenerateImageUpdates(sceneImageTaskId);

                }
            }
            
        } catch (err) {
            console.log('websocket is not JSON');
        }
    }

}