define(["jquery"], function ($) {
    console.log("partner carousel has been loaded");

    var sponsorInterval = null;

    $(document).ready(function () {
        var activeSponsors = $('.sponsorsBanner:visible').attr('id');

        var rotateSponsors = function () {
            $("#" + activeSponsors + " li.active").removeClass('active')
                .next().add("#" + activeSponsors + " li:first").last().addClass("active");
        }

        function resizedw() {
            var currentActive = $('.sponsorsBanner:visible').attr('id');

            if (activeSponsors !== $('.sponsorsBanner:visible').attr('id')) {
                activeSponsors = currentActive;
                clearTimeout(sponsorInterval);
                if (toggleSlide != undefined) {
                    sponsorInterval = setInterval(toggleSlide, 3000);
                }
            }
        }

        window.onresize = function () {
            clearTimeout(doit);
            var doit = setTimeout(resizedw, 100);
        };

        sponsorInterval = setInterval(rotateSponsors, 3000);

    });
});