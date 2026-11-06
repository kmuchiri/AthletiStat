define(["jquery"], function ($) {

    // jquery has been loaded
    console.log("by-category has been loaded");
    const areaRecords = "0";


    $("#byCategoryCategoriesDropDown").change(function () {
        if (this.value !== areaRecords) {
            $("#categoryRegionDiv").hide();
            const urlArray = window.location.pathname.split("/");
            let newUrl = "/";
            urlArray.pop();
            $.each(urlArray,
                function(index, value) {
                    if (value !== "") {
                        newUrl = newUrl + value + "/";
                    }
                });
            newUrl = newUrl + this.value;
            window.location.href = newUrl;
        } else {
            $("#categoryRegionDiv").show();

            const urlArray = window.location.pathname.split("/");
            let newUrl = "/";
            urlArray.pop();
            $.each(urlArray,
                function (index, value) {
                    if (value !== "") {
                        newUrl = newUrl + value + "/";
                    }
                });
            newUrl = newUrl + $("#byCategoryRegionDropDown").val();

            window.location.href = newUrl;
        }
    });

    $("#byCategoryRegionDropDown").change(function() {
        const urlArray = window.location.pathname.split("/");
        let newUrl = "/";
        urlArray.pop();
        $.each(urlArray,
            function (index, value) {
                if (value !== "") {
                    newUrl = newUrl + value + "/";
                }
            });
        newUrl = newUrl + $("#byCategoryRegionDropDown").val();
        window.location.href = newUrl;
    });



    selectCategoryCategoriesDropDown();
});

function selectCategoryCategoriesDropDown() {
    const urlArray = window.location.pathname.split("/");
    const currenturlSlug = urlArray.pop();
 
    $('#byCategoryRegionDropDown option').each(function () {
        if (currenturlSlug === $(this).attr('value')) {
            $("#byCategoryCategoriesDropDown").val("0");
            $("#byCategoryRegionDropDown").val(window.location.pathname.split("/").pop());
            $("#categoryRegionDiv").show();
        }
    });

    if ($("#byCategoryCategoriesDropDown").val() !== "0") {
        $("#byCategoryCategoriesDropDown").val(window.location.pathname.split("/").pop());
        $("#categoryRegionDiv").hide();
    } 

}

 

function redirectPage(params) {
    let timeout = 0;

    if ($("#overlay").length > 0) {
        document.getElementById("overlay").style.display = "block";
        timeout = 300;
    }

    setTimeout(function() {
        let esc = encodeURIComponent;
        let query = Object.keys(params)
            .map(function (x) {
                if (esc(params[x]) == "null") {
                    params[x] = "";
                }
                return esc(x) + '=' + esc(params[x]);
            })
            .join('&');

        console.log(query);

        const lastSlashIndex = window.location.pathname.lastIndexOf("/");
        const totalLength = window.location.pathname.length;
        let lastString = window.location.pathname.substring(lastSlashIndex + 1);
        if ($.isNumeric(lastString)) {
            lastString = window.location.pathname.slice(0, (lastString.length * -1) + -1);
            window.location.href = window.location.origin + lastString + "?" + query;
        }
        else {
            if (window.location.pathname.toLowerCase().indexOf("heritage/plaque/") > 0) {
                window.location.href = window.location.origin + window.location.pathname + "?" + query;
            } else {
                window.location.href = window.location.origin + "/heritage/plaque" + "?" + query;
            }

        }

    }, timeout);
    
}




function isEmpty(str) {
    return (!str || 0 === str.length);
}