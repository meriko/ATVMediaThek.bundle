TITLE = 'ATV MediaThek'
ART   = 'art-default.jpg'
ICON  = 'icon-default.png'

HTTP_USER_AGENT = "Mozilla/5.0 (iPad; CPU OS 7_0 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11A465 Safari/9537.53"
BASE_URL = "http://atv.at"
PREFIX = '/video/atv'

VIDEOS_PER_PAGE = 25
SITE_VIDEOS_PER_PAGE = 6


SHOW_SUM = "showsum"
DICT_V = 1

SEARCH_URL = BASE_URL + '/suche/%s?ext_search_submit=true&clip_page=%i&user_page=1&content_page=1&searchterm=%s&videos=1&v_atv_content=1&v_user_content=1&v_region=&m_region=&m_gender=&m_from_age='

RE_ART = Regex('background-image: *url\((http.*\.jpg)\);')

##########################################################################################
def Start():
    # Setup the default attributes for the ObjectContainer
    ObjectContainer.title1 = TITLE
    ObjectContainer.art    = R(ART)

    # Setup the default attributes for the other objects
    DirectoryObject.thumb = R(ICON)
    DirectoryObject.art   = R(ART)

    HTTP.CacheTime             = CACHE_1HOUR
    HTTP.Headers['User-agent'] = HTTP_USER_AGENT
    
    if not "version" in Dict:
        Log("No version number in dict, resetting")
        Dict.Reset()
        Dict["version"] = DICT_V
        Dict.Save()

    if Dict["version"] != DICT_V:
        Log("Wrong version number in dict, resetting")
        Dict.Reset()
        Dict["version"] = DICT_V
        Dict.Save()

    if not SHOW_SUM in Dict:
        Log("No summary dictionary, creating")
        Dict[SHOW_SUM] = {}
        Dict.Save()

    Thread.Create(HarvestShowData)

##########################################################################################
@handler(PREFIX, TITLE, thumb = ICON, art = ART)
def MainMenu():
    oc = ObjectContainer()

    if Client.Platform == 'Android':
        oc.header  = 'Not supported'
        oc.message = 'This channel is not supported on Android clients'
        
        return oc

    #title = "Suche"
    #oc.add(
    #    InputDirectoryObject(
    #        key = Callback(Search),
    #        title = title, 
    #        prompt = title,
    #        thumb = R(ICON)
    #    )
    #)
    
    for object in Programs().objects:
        oc.add(object) 
    
    return oc

###################################################################################################
@route(PREFIX + '/Programs')
def Programs():
    oc = ObjectContainer()
    
    pageElement = HTML.ElementFromURL(BASE_URL + '/mediathek')
    
    for item in pageElement.xpath("//*[@class='program']"):
        url = item.xpath(".//a/@href")[0]
        
        if not url.startswith("http"):
            url = BASE_URL + url
        
        title = unicode(item.xpath(".//*[@class='program_title']/text()")[0].strip())
        thumb = item.xpath(".//img/@src")[0]
        
        oc.add(
            DirectoryObject(
                key =
                    Callback(
                        Videos,
                        url = url,
                        title = title,
                        thumb = thumb,
                        art = GetShowArtUrl(title)
                    ),
                title = title,
                thumb = thumb,
                summary = GetShowSummary(title),
                art = GetShowArtUrl(title)
            )
        )
        
    return oc

###################################################################################################
@route(PREFIX + '/Search', page = int)
def Search(query, page = 1):
    oc = ObjectContainer()
    
    searchURL = SEARCH_URL % (String.Quote(query), page, String.Quote(query, usePlus = True))
    
    pageElement = HTML.ElementFromURL(searchURL)
    
    for item in pageElement.xpath("//*[contains(@class, 'video_list')]//li"):
        try:
            url = item.xpath(".//a/@href")[0].replace("/0/1", "")
            if not url.startswith("http"):
                url = BASE_URL + url
                
            title = ''.join(item.xpath(".//a/text()")).strip()
        except:
            continue
        
        try:
            show = item.xpath(".//img/@alt")[0].strip()
        except:
            show = None
            
        try:
            thumb = item.xpath(".//img/@src")[0]
            if not thumb.startswith("http"):
                thumb = BASE_URL + thumb
        except:
            thumb = None

        oc.add(
            EpisodeObject(
                url = url,
                title = title,
                show = show,
                thumb = thumb
            )
        )
        
    if len(oc) > 0:
        if page > 1:
            # Remove first video since it is a duplicate
            # of the last one in the previous page
            oc.objects = oc.objects[1:]
                    
        if pageElement.xpath("//*[@class='next_page']"):
            oc.add(
                NextPageObject(
                    key =
                        Callback(
                            Search,
                            query = query,
                            page = page + 1
                        )
                )
            )
            
        return oc
    else:
        oc = ObjectContainer(title2 = unicode(query))
        oc.header  = 'Sorry'
        oc.message = 'Nothing found for "' + unicode(query) + '"'
        
        return oc

##########################################################################################
@route(PREFIX + '/Videos', page = int, offset = int)
def Videos(url, title, thumb, art, page = 1, contentset_id = None, offset = 0):
    oc = ObjectContainer(title2 = unicode(title))

    if not contentset_id:
        element = HTML.ElementFromURL(url)
        contentset_id = element.xpath("//section/@id")[0].replace("pi_", "")
    
    show = title
    
    requiredPages = (VIDEOS_PER_PAGE / SITE_VIDEOS_PER_PAGE) + 1
    
    for i in range(requiredPages):
        content = HTTP.Request('http://atv.at/uri/fepe/%s/?page=%i' % (contentset_id, page)).content
        
        if not 'video' in content:
            break
             
        element = HTML.ElementFromString(content)
        
        noVideos = 0
        
        for item in element.xpath("//*[@class='teaser']")[offset:]:
            videoURL = item.xpath(".//a/@href")[0]
            
            if not videoURL.startswith("http"):
                videoURL = BASE_URL + videoURL
            
            videoTitle = unicode(item.xpath(".//*[@class='title']/text()")[0])
            videoThumb = item.xpath(".//img/@src")[0]
            
            try:
                index = int(videoTitle.split(" ")[1])
            except:
                index = None
            
            oc.add(
                EpisodeObject(
                    url = videoURL,
                    title = videoTitle,
                    thumb = videoThumb,
                    index = index,
                    show = show,
                    art = art
                )
            )
            
            noVideos = noVideos + 1
            
            if len(oc) >= VIDEOS_PER_PAGE:
                oc.add(
                    NextPageObject(
                        key =
                            Callback(
                                Videos,
                                url = url,
                                title = show,
                                thumb = thumb,
                                art = art,
                                page = page,
                                contentset_id = contentset_id,
                                offset = noVideos
                            )
                    )
                )
                
                break
        
        page = page + 1
        offset = 0
        
    if len(oc) < 1:
        oc.header  = 'Sorry'
        oc.message = 'Could not find any content'
    
    return oc      

##########################################################################################
def HarvestShowData():
    programs_oc = Programs()
    
    for program_do in programs_oc.objects:
        query = String.Unquote((program_do.key).split("?")[1])
        showURL = String.ParseQueryString(query)['url'][0]
        showName = unicode(program_do.title)

        d = Dict[SHOW_SUM]
        if showName in d:
            td = Datetime.Now() - d[showName][2]
            if td.days < 30:
                Log("Got cached data for %s" % showName)
                continue
        else:
            Log("no hit for %s" % showName)

        pageElement = HTML.ElementFromURL(showURL)

        #Find the summary for the show
        summary = unicode(pageElement.xpath('//meta[@property="og:description"]/@content')[0])

        imgUrl = unicode(program_do.thumb)
        
        try:
            art = unicode(RE_ART.search(HTML.StringFromElement(pageElement)).groups()[0])
        except:
            art = None

        t = Datetime.TimestampFromDatetime(Datetime.Now())
        d[showName] = (showName, summary, Datetime.Now(), imgUrl, art)

        #To prevent this thread from stealing too much network time
        #we force it to sleep for every new page it loads
        Dict[SHOW_SUM] = d
        Dict.Save()
        Thread.Sleep(1)
            
def GetShowSummary(showName):
    d = Dict[SHOW_SUM]
    showName = unicode(showName)
    if showName in d:
        return d[showName][1]
    return ""

def GetShowImgUrl(showName):
    d = Dict[SHOW_SUM]
    showName = unicode(showName)
    if showName in d:
        return d[showName][3]
    return None
    
def GetShowArtUrl(showName):
    d = Dict[SHOW_SUM]
    showName = unicode(showName)
    if showName in d:
        return d[showName][4]
    return None

 