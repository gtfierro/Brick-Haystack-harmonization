#! /usr/bin/env node

let fs = require('fs');
let path = require('path');
let os  = require('os');

// utility to force a path to a directory
let toDir = function(f)
{
  if (os.platform() == "win32") {
    // change to posix-style path
    f = f.split(path.sep).join(path.posix.sep);
  }
  // ensure ends with a trailing '/' for a directory
  if (!f.endsWith("/")) f = f + "/";
  return f;
}


// bootstrap Env dirs.
let fan_home = process.env["FAN_HOME"];
if (!fan_home)
{
  // Assumes you are running this script in <fan_home>/bin/
  fan_home = path.resolve(__dirname, "../");
}

// modify module search path to include <fan_home>/lib/js/node_modules/
module.paths = [path.resolve(fan_home, "lib/js/node_modules")].concat(module.paths);

// require core pods and configure Env
let fan = require('fan.js');
fan_home = toDir(fan_home);
fan.sys.Env.cur().m_homeDir = fan.sys.File.os(toDir(fan_home));
fan.sys.Env.cur().m_workDir = fan.sys.File.os(toDir(fan_home));
fan.sys.Env.cur().m_tempDir = fan.sys.File.os(toDir(path.resolve(fan_home, "temp")));

// require some pods that are used by type reflection
// TODO: could iterate node_modules/ directory and require them all
require('graphics');
require('hxData');
require('hxIO');

// get args to pass to program
// - arvg[0] = node.exe
// - argv[1] is this script
// - argv[2] is the type/qname to run
// - argv[3..-1] are the args to pass to the type
let args = fan.sys.List.make(fan.sys.Str.$type, process.argv.slice(3));

// get type to run
let spec = process.argv[2];
if (!spec)
{
  console.log(
'usage:\n \
  node fan.js <pod>[::<type>[.method]] [args]*\n');
  return 1;
}
var [pod, type] = spec.split('::')
if (!type) type = 'Main.main';
var [type, slot] = type.split('.');
if (!slot) slot = 'main';

// require the pod
require(`${pod}.js`);

// launch it!
type   = fan.sys.Type.find(`${pod}::${type}`);
method = type.method(slot);
type.make()[method.$name()](args);
