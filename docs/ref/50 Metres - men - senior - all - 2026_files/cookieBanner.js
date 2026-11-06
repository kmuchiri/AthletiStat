define(['jquery'], function ($) {
    //tiny cookie.js library
    // Copyright (c) 2015 Florian Hartmann, https://github.com/florian https://github.com/florian/cookie.js
    !function (a, b) { var c = function () { return c.get.apply(c, arguments) }, d = c.utils = { isArray: Array.isArray || function (a) { return "[object Array]" === Object.prototype.toString.call(a) }, isPlainObject: function (a) { return !!a && "[object Object]" === Object.prototype.toString.call(a) }, toArray: function (a) { return Array.prototype.slice.call(a) }, getKeys: Object.keys || function (a) { var b = [], c = ""; for (c in a) a.hasOwnProperty(c) && b.push(c); return b }, encode: function (a) { return String(a).replace(/[,;"\\=\s%]/g, function (a) { return encodeURIComponent(a) }) }, decode: function (a) { return decodeURIComponent(a) }, retrieve: function (a, b) { return null == a ? b : a } }; c.defaults = {}, c.expiresMultiplier = 86400, c.set = function (c, e, f) { if (d.isPlainObject(c)) for (var g in c) c.hasOwnProperty(g) && this.set(g, c[g], e); else { f = d.isPlainObject(f) ? f : { expires: f }; var h = f.expires !== b ? f.expires : this.defaults.expires || "", i = typeof h; "string" === i && "" !== h ? h = new Date(h) : "number" === i && (h = new Date(+new Date + 1e3 * this.expiresMultiplier * h)), "" !== h && "toGMTString" in h && (h = ";expires=" + h.toGMTString()); var j = f.path || this.defaults.path; j = j ? ";path=" + j : ""; var k = f.domain || this.defaults.domain; k = k ? ";domain=" + k : ""; var l = f.secure || this.defaults.secure ? ";secure" : ""; f.secure === !1 && (l = ""), a.cookie = d.encode(c) + "=" + d.encode(e) + h + j + k + l } return this }, c.setDefault = function (a, e, f) { if (d.isPlainObject(a)) { for (var g in a) this.get(g) === b && this.set(g, a[g], e); return c } if (this.get(a) === b) return this.set.apply(this, arguments) }, c.remove = function (a) { a = d.isArray(a) ? a : d.toArray(arguments); for (var b = 0, c = a.length; b < c; b++) this.set(a[b], "", -1); return this }, c.removeSpecific = function (a, b) { if (!b) return this.remove(a); a = d.isArray(a) ? a : [a], b.expires = -1; for (var c = 0, e = a.length; c < e; c++) this.set(a[c], "", b); return this }, c.empty = function () { return this.remove(d.getKeys(this.all())) }, c.get = function (a, b) { var c = this.all(); if (d.isArray(a)) { for (var e = {}, f = 0, g = a.length; f < g; f++) { var h = a[f]; e[h] = d.retrieve(c[h], b) } return e } return d.retrieve(c[a], b) }, c.all = function () { if ("" === a.cookie) return {}; for (var b = a.cookie.split("; "), c = {}, e = 0, f = b.length; e < f; e++) { var g = b[e].split("="), h = d.decode(g.shift()), i = d.decode(g.join("=")); c[h] = i } return c }, c.enabled = function () { if (navigator.cookieEnabled) return !0; var a = "_" === c.set("_", "_").get("_"); return c.remove("_"), a }, window.cookie = c }("undefined" == typeof document ? null : document);

    var key = 'iaaf-cookie-banner';

    function setCookie(cname, cvalue, exdays) {
        var d = new Date();
        d.setTime(d.getTime() + (exdays*24*60*60*1000));
        var expires = "expires="+ d.toUTCString();
        document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
    }

    function getCookie(cname) {
        var name = cname + "=";
        var decodedCookie = decodeURIComponent(document.cookie);
        var ca = decodedCookie.split(';');
        for(var i = 0; i <ca.length; i++) {
            var c = ca[i];
            while (c.charAt(0) == ' ') {
                c = c.substring(1);
            }
            if (c.indexOf(name) == 0) {
                return c.substring(name.length, c.length);
            }
        }
        return "";
    }
    
    if (getCookie(key) === "") {
        var html = "<div class='cookie-banner'>" +
                "<p class='cookie__text'>We use cookies to improve your experience. By using our site you are accepting our <a href='https://worldathletics.org/cookies-policy'>Cookie Policy</a></p>" +
                "<div class='close-banner btn btn-lg'>Continue</div>" +
            "</div>";

        var $banner = $(html);
        var body = $('body');
        var compBanner = $('.comp-banner');
        var isComp = /competitions\//.test(window.location.href);
        var bannerCss = {
            color: '#fff',
            position: 'fixed',
            left: 0,
            backgroundColor: '#000026',
            padding: '10px',
            zIndex: '999',
            width: '100%',
            textAlign: 'center'
        };

        if (isComp) {
            bannerCss.position = 'absolute';
        }

        $banner.css(bannerCss);

        $banner.children()
        .css({
            display: 'inline-block',
            margin: '0 5px',
            width: 'auto'
        })
        .find('a')
        .css({
            color: '#fff'
        });

        body.append($banner);

        handleHeights();

        $(document).one('click', '.close-banner', function () {
            setCookie(key, true, 30 * 6);

            $('.cookie-banner').slideUp(350);
            if (isComp) {
                $('.comp-banner').animate({
                    marginTop: 0
                }, 350);
            } else {
                body.animate({
                    paddingTop: 0
                }, 350);
            }

            window.removeEventListener('resize', handleDebounce);
            
        });

        function handleHeights() {
            var bannerHeight = ($banner[0].offsetHeight - 1) + 'px';
            if (isComp) {
                compBanner.css('margin-top', bannerHeight);
            } else {
                body.css('padding-top', bannerHeight);
            }
        }

        var debounce = void 0;
        window.addEventListener('resize', handleDebounce);

        function handleDebounce() {
            clearTimeout(debounce);

            debounce = setTimeout(handleHeights, 250);
        }
    }
});