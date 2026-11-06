define(["jquery"], function ($) {
    console.log("homev2 has been loaded");

    if (iaaf.hideMenuSecondRow === "true") {
        $(".sub-navs").html("");
 

        setTimeout(function () {
            $(".sub-navs").html("");
        }, 500);
    }

    if ($(".carouselImage").length > 0) {

        $(".sub-navs").html("");


        setTimeout(function () {
            $(".sub-navs").html("");
        }, 500);
    }
});
 
