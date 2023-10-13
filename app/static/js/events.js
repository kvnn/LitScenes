
var socket = io();
socket.on('connect', function() {
    console.log('socketio connected');
});

// Listen for task_progress events
socket.on('task_process_book_progress', function(data) {
    console.log('Received task_process_book_progress event: ' + JSON.stringify(data));
    // Update the UI with the progress
    document.getElementById("progressBar").value = data.progress;
});

// Listen for task_complete events
socket.on('task_process_book_complete', function(data) {
    console.log('Received task_process_book_complete event: ' + JSON.stringify(data));
    // Handle task completion, e.g., show a notification
    alert("Task completed!");
});

socket.on('error', function(error) {
    console.error('Socket.IO Error:', error);
});