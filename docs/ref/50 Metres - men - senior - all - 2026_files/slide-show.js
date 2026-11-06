"use strict";
function fadeSlideShow(a) {
    this.setting = a;
    a = null;
    var b = this.setting;
    b.fadeduration = b.fadeduration ? parseInt(b.fadeduration) : 500;
    b.curimage = b.persist ? fadeSlideShow.routines.getCookie("gallery-" + b.wrapperid) : 0;
    b.curimage = b.curimage || 0;
    b.currentstep = 0;
    b.totalsteps = b.imagearray.length * (b.displaymode.cycles > 0 ? b.displaymode.cycles : Infinity);
    b.fglayer = 0, b.bglayer = 1;
    b.oninit = b.oninit || function () { };
    b.onslide = b.onslide || function () { };
    if (b.displaymode.randomize) b.imagearray.sort(function () {
        return .5 - Math.random()
    });
    var c = [];
    b.longestdesc = "";
    for (var d = 0; d < b.imagearray.length; d++) {
        c[d] = new Image;
        c[d].src = b.imagearray[d][0];
        if (b.imagearray[d][3] && b.imagearray[d][3].length > b.longestdesc.length) b.longestdesc = b.imagearray[d][3]
    }
    var e = fadeSlideShow_descpanel.controls[0];
    b.closebutton = b.descreveal == "always" ? '<img class="close" src="' + e[0] + '" style="float:right;cursor:hand;cursor:pointer;width:100%; height:108px;margin-left:2px" title="Hide Description" />' : "";
    var f = this;
    jQuery(document).ready(function (a) {
        var b = f.setting;
        var c = fadeSlideShow.routines.getFullHTML(b.imagearray);
        b.$wrapperdiv = a("#" + b.wrapperid).css({
            position: "relative",
            visibility: "visible",
            background: "white",
            overflow: "hidden",
            width: "100%",
            height: b.dimensions[1]
        }).empty();
        if (b.$wrapperdiv.length == 0) {
            alert('Error: DIV with ID "' + b.wrapperid + '" not found on page.');
            return
        }
        b.$gallerylayers = a('<div class="gallerylayer"></div><div class="gallerylayer"></div>').css({
            position: "absolute",
            left: 0,
            top: 0,
            width: "100%",
            height: "100%",
            background: "white"
        }).appendTo(b.$wrapperdiv);
        var d = a('<img src="' + fadeSlideShow_descpanel.controls[2][0] + '" style="position:absolute;width:' + fadeSlideShow_descpanel.controls[2][1] + ";height:" + fadeSlideShow_descpanel.controls[2][2] + '" />').css({
            left: b.dimensions[0] / 2 - fadeSlideShow_descpanel.controls[2][1] / 2,
            top: b.dimensions[1] / 2 - fadeSlideShow_descpanel.controls[2][2]
        }).appendTo(b.$wrapperdiv);
        var e = b.$gallerylayers.html(c).find("img").hide().eq(b.curimage);
        if (b.longestdesc != "" && b.descreveal != "none") {
            fadeSlideShow.routines.adddescpanel(a, b);
            if (b.descreveal == "always") {
                b.$descpanel.css({
                    top: b.dimensions[1] - b.panelheight
                });
                b.$descinner.click(function (a) {
                    if (a.target.className == "close") {
                        f.showhidedescpanel("hide")
                    }
                });
                b.$restorebutton.click(function (b) {
                    f.showhidedescpanel("show");
                    a(this).css({
                        visibility: "hidden"
                    })
                })
            } else if (b.descreveal == "ondemand") {
                b.$wrapperdiv.bind("mouseenter", function () {
                    f.showhidedescpanel("show")
                });
                b.$wrapperdiv.bind("mouseleave", function () {
                    f.showhidedescpanel("hide")
                })
            }
        }
        b.$wrapperdiv.bind("mouseenter", function () {
            b.ismouseover = false
        });
        b.$wrapperdiv.bind("mouseleave", function () {
            b.ismouseover = false
        });
        if (e.get(0).complete) {
            d.hide();
            f.paginateinit(a);
            f.showslide(b.curimage)
        } else {
            d.hide();
            f.paginateinit(a);
            e.bind("load", function () {
                f.showslide(b.curimage)
            })
        }
        b.oninit.call(f);
        a(window).bind("unload", function () {
            if (f.setting.persist) fadeSlideShow.routines.setCookie("gallery-" + b.wrapperid, b.curimage);
            jQuery.each(f.setting, function (a) {
                if (f.setting[a] instanceof Array) {
                    for (var b = 0; b < f.setting[a].length; b++) {
                        if (f.setting[a][b].tagName == "DIV") f.setting[a][b].innerHTML = null;
                        f.setting[a][b] = null
                    }
                }
            });
            f = f.setting = null
        })
    })
}

var fadeSlideShow_descpanel = {
    controls: [
        ["x.png", 7, 7],
        ["restore.png", 10, 11],
        ["/Areas/Competitions/Assets/images/layout/loading.gif", 54, 55]
    ],
    fontStyle: "normal 11px Verdana",
    slidespeed: 200
};

fadeSlideShow.prototype = {
    navigate: function (a) {
        var b = this.setting;
        clearTimeout(b.playtimer);
        if (b.displaymode.type == "auto") {
            b.displaymode.type = "manual";
            b.displaymode.wraparound = true
        }
        if (!isNaN(parseInt(a))) {
            this.showslide(parseInt(a))
        } else if (/(prev)|(next)/i.test(a)) {
            this.showslide(a.toLowerCase())
        }
    },
    showslide: function (a) {
        var b = this;
        var c = b.setting;
        if (c.displaymode.type == "auto" && c.ismouseover && c.currentstep <= c.totalsteps) {
            c.playtimer = setTimeout(function () {
                b.showslide("next")
            }, c.displaymode.pause);
            return
        }
        var d = c.imagearray.length;
        var e = a == "next" ? c.curimage < d - 1 ? c.curimage + 1 : 0 : a == "prev" ? c.curimage > 0 ? c.curimage - 1 : d - 1 : Math.min(a, d - 1);
        var f = c.$gallerylayers.eq(c.bglayer).find("img").hide().eq(e).show();
        var g = [f.width(), f.height()];
        f.css({
            marginLeft: g[0] > 0 && g[0] < c.dimensions[0] ? c.dimensions[0] / 2 - g[0] / 2 : 0
        });
        f.css({
            marginTop: g[1] > 0 && g[1] < c.dimensions[1] ? c.dimensions[1] / 2 - g[1] / 2 : 0
        });
        if (c.descreveal == "peekaboo" && c.longestdesc != "") {
            clearTimeout(c.hidedesctimer);
            b.showhidedescpanel("hide", 0)
        }
        c.$gallerylayers.eq(c.bglayer).css({
            zIndex: 3,
            opacity: 0
        }).stop().css({
            opacity: 0
        }).animate({
            opacity: 1
        }, c.fadeduration, function () {
            clearTimeout(c.playtimer);
            try {
                c.onslide.call(b, c.$gallerylayers.eq(c.fglayer).get(0), c.curimage)
            } catch (a) {
                alert('Fade In Slideshow error: An error has occured somwhere in your code attached to the "onslide" event: ' + a)
            }
            if (c.descreveal == "peekaboo" && c.longestdesc != "") {
                b.showhidedescpanel("show");
                c.hidedesctimer = setTimeout(function () {
                    b.showhidedescpanel("hide")
                }, c.displaymode.pause - fadeSlideShow_descpanel.slidespeed)
            }
            c.currentstep += 1;
            if (c.displaymode.type == "auto") {
                if (c.currentstep <= c.totalsteps || c.displaymode.cycles == 0) c.playtimer = setTimeout(function () {
                    b.showslide("next")
                }, c.displaymode.pause)
            }
        });
        c.$gallerylayers.eq(c.fglayer).css({
            zIndex: 1
        });
        c.fglayer = c.bglayer;
        c.bglayer = c.bglayer == 0 ? 1 : 0;
        c.curimage = e;
        if (c.$descpanel) {
            c.$descpanel.css({
                visibility: c.imagearray[e][3] ? "visible" : "hidden"
            });
            if (c.imagearray[e][3]) c.$descinner.empty().html(c.closebutton + c.imagearray[e][3])
        }
        if (c.displaymode.type == "manual" && !c.displaymode.wraparound) {
            this.paginatecontrol()
        }
        if (c.$status) c.$status.html(c.curimage + 1 + "/" + d)
    },
    showhidedescpanel: function (a, b) {
        var c = this.setting;
        var d = a == "show" ? c.dimensions[1] - c.panelheight : this.setting.dimensions[1];
        c.$descpanel.stop().animate({
            top: d
        }, typeof b != "undefined" ? b : fadeSlideShow_descpanel.slidespeed, function () {
            if (c.descreveal == "always" && a == "hide") c.$restorebutton.css({
                visibility: "visible"
            })
        })
    },
    paginateinit: function (a) {
        var b = this;
        var c = this.setting;
        if (c.togglerid) {
            c.$togglerdiv = a("#" + c.togglerid);
            c.$prev = c.$togglerdiv.find(".prev").data("action", "prev");
            c.$next = c.$togglerdiv.find(".next").data("action", "next");
            c.$prev.add(c.$next).click(function (c) {
                var d = a(this);
                b.navigate(d.data("action"));
                c.preventDefault()
            });
            c.$status = c.$togglerdiv.find(".status")
        }
    },
    paginatecontrol: function () {
        var a = this.setting;
        a.$prev.css({
            opacity: a.curimage == 0 ? .4 : 1
        }).data("action", a.curimage == 0 ? "none" : "prev");
        a.$next.css({
            opacity: a.curimage == a.imagearray.length - 1 ? .4 : 1
        }).data("action", a.curimage == a.imagearray.length - 1 ? "none" : "next");
        if (document.documentMode == 8) {
            a.$prev.find("img:eq(0)").css({
                opacity: a.curimage == 0 ? .4 : 1
            });
            a.$next.find("img:eq(0)").css({
                opacity: a.curimage == a.imagearray.length - 1 ? .4 : 1
            })
        }
    }
};
fadeSlideShow.routines = {
    getSlideHTML: function (a) {
        var b = a[1] ? '<a href="' + a[1] + '" target="' + a[2] + '" role="link"' + '" aria-label="' + a[3] + '">\n' : "";
        b += '<img alt="' + a[3] + '" src="' + a[0] + '" style="border-width:0;" />\n';
        b += a[1] ? "</a>\n" : "";
        return b
    },
    getFullHTML: function (a) {
        var b = "";
        for (var c = 0; c < a.length; c++) b += this.getSlideHTML(a[c]);
        return b
    },
    adddescpanel: function (a, b) {
        b.$descpanel = a('<div class="fadeslidedescdiv"></div>').css({
            position: "absolute",
            visibility: "hidden",
            width: "100%",
            left: 0,
            top: b.dimensions[1],
            font: fadeSlideShow_descpanel.fontStyle,
            zIndex: "2"
        }).appendTo(b.$wrapperdiv);
        a('<div class="descpanelbg"></div><div class="descpanelfg"></div>').css({
            position: "absolute",
            left: 0,
            top: 0,
            width: b.$descpanel.width() - 8,
            padding: "4px"
        }).eq(0).css({
            background: "transparent",
            opacity: .7
        }).end().eq(1).css({
            color: "white"
        }).html(b.closebutton + b.longestdesc).end().appendTo(b.$descpanel);
        b.$descinner = b.$descpanel.find("div.descpanelfg");
        b.panelheight = b.$descinner.outerHeight();
        b.$descpanel.css({
            height: b.panelheight
        }).find("div").css({
            height: "100%"
        });
        if (b.descreveal == "always") {
            b.$restorebutton = a('<img class="restore" title="Restore Description" src="' + fadeSlideShow_descpanel.controls[1][0] + '" style="position:absolute;visibility:hidden;right:0;bottom:0;width:' + fadeSlideShow_descpanel.controls[1][1] + "px;height:" + fadeSlideShow_descpanel.controls[1][2] + 'px;cursor:pointer;cursor:hand" />').appendTo(b.$wrapperdiv)
        }
    },
    getCookie: function (a) {
        var b = new RegExp(a + "=[^;]+", "i");
        if (document.cookie.match(b)) return document.cookie.match(b)[0].split("=")[1];
        return null
    },
    setCookie: function (a, b) {
        document.cookie = a + "=" + b + ";path=/"
    }
}