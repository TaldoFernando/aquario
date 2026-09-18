const {test}=require('node:test'),assert=require('node:assert/strict');
const {phase}=require('../extension/solar.js');
test('Equinox at equator: noon vs midnight',()=>{assert(phase(new Date('2026-03-20T12:00:00Z'),{latitude:0,longitude:0}).light>.95);assert(phase(new Date('2026-03-20T00:00:00Z'),{latitude:0,longitude:0}).light<.1);});
test('Fortaleza solar noon in UTC-3',()=>{assert(phase(new Date('2026-09-16T15:00:00Z'),{latitude:-3.73,longitude:-38.52}).light>.95);assert(phase(new Date('2026-09-16T03:00:00Z'),{latitude:-3.73,longitude:-38.52}).light<.1);});
test('Polar day and polar night remain finite',()=>{assert(phase(new Date('2026-06-21T00:00:00Z'),{latitude:89,longitude:0}).light>.95);assert(phase(new Date('2026-12-21T12:00:00Z'),{latitude:89,longitude:0}).light<.1);});
test('Missing geolocation explicitly uses local time',()=>{assert(phase(new Date(),null).label.includes('sem localização'));});
