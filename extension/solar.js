// NOAA fractional-year solar approximation. Longitude east is positive.
(function (root) {
  function phase(date, geo) {
    if (!geo || !Number.isFinite(geo.latitude) || !Number.isFinite(geo.longitude)) {
      const h = date.getHours() + date.getMinutes()/60;
      return {light: h >= 7 && h < 18 ? 1 : h >= 6 && h < 19 ? .45 : .08, label: 'Horário local · sem localização'};
    }
    const year = date.getUTCFullYear();
    const day = Math.floor((Date.UTC(year,date.getUTCMonth(),date.getUTCDate())-Date.UTC(year,0,0))/86400000);
    const days = new Date(Date.UTC(year,1,29)).getUTCMonth() === 1 ? 366 : 365;
    const hour = date.getUTCHours()+date.getUTCMinutes()/60+date.getUTCSeconds()/3600;
    const g = 2*Math.PI/days*(day-1+(hour-12)/24);
    const eq = 229.18*(.000075+.001868*Math.cos(g)-.032077*Math.sin(g)-.014615*Math.cos(2*g)-.040849*Math.sin(2*g));
    const dec = .006918-.399912*Math.cos(g)+.070257*Math.sin(g)-.006758*Math.cos(2*g)+.000907*Math.sin(2*g)-.002697*Math.cos(3*g)+.00148*Math.sin(3*g);
    const minutes = ((hour*60+eq+4*geo.longitude)%1440+1440)%1440;
    const ha = (minutes/4-180)*Math.PI/180;
    const lat = geo.latitude*Math.PI/180;
    const altitude = Math.asin(Math.max(-1,Math.min(1,Math.sin(lat)*Math.sin(dec)+Math.cos(lat)*Math.cos(dec)*Math.cos(ha))))*180/Math.PI;
    const light = .08+.92*Math.max(0,Math.min(1,(altitude+6)/18));
    return {light, altitude, label: altitude < -6 ? 'Noite tranquila' : altitude < 6 ? 'Luz do horizonte' : 'Luz do dia'};
  }
  root.AquarioSolar = {phase};
  if (typeof module !== 'undefined') module.exports = {phase};
})(globalThis);
