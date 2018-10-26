// Modules to control application life and create native browser window
const {app, BrowserWindow} = require('electron')
const path = require("path");
const url = require("url");
const { spawn } = require('child_process');

// Keep a global reference of the window object, if you don't, the window will
// be closed automatically when the JavaScript object is garbage collected.
let mainWindow
let backend

function startLocalBackend() {
    backend = spawn('../../bin/bundle-app', ['--port=4254', '--no-static-files', '--no-open-url']);

    backend.stdout.on('data', (data) => {
      console.log(`stdout: ${data}`);
    });

    backend.stderr.on('data', (data) => {
      console.log(`stderr: ${data}`);
    });

    backend.on('close', (code) => {
      console.log(`child process exited with code ${code}`);
    });
}

function createWindow () {
  // Create the browser window.
  mainWindow = new BrowserWindow({width: 1124, height: 600})

  // and load the index.html of the app
  mainWindow.loadURL(
    url.format({
      pathname: path.join(__dirname, `/dist/ng-bundle/index.html`),
      protocol: "file:",
      slashes: true
    })
  );

  // Open the DevTools.
  // mainWindow.webContents.openDevTools()

  // Emitted when the window is closed.
  mainWindow.on('closed', function () {
    // Dereference the window object, usually you would store windows
    // in an array if your app supports multi windows, this is the time
    // when you should delete the corresponding element.
    mainWindow = null
  })
}

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.on('ready', createWindow)

// Quit when all windows are closed.
app.on('window-all-closed', function () {
  // On OS X it is common for applications and their menu bar
  // to stay active until the user quits explicitly with Cmd + Q
  if (process.platform !== 'darwin') {
    app.quit()
  }
  if (backend) {
    backend.kill()
  }
})

app.on('activate', function () {
  // On OS X it's common to re-create a window in the app when the
  // dock icon is clicked and there are no other windows open.
  if (mainWindow === null) {
    createWindow()
  }
})

// In this file you can include the rest of your app's specific main process
// code. You can also put them in separate files and require them here.
startLocalBackend()
