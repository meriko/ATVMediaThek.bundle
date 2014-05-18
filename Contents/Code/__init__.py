GetVideoData = SharedCodeService.atv.GetVideoData

TITLE = 'ATV MediaThek'
ART   = 'art-default.jpg'
ICON  = 'icon-default.png'

HTTP_USER_AGENT = "Mozilla/5.0 (iPad; CPU OS 7_0 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11A465 Safari/9537.53"
BASE_URL = "http://atv.at"
PREFIX = '/video/atv'

VIDEOS_PER_PAGE = 25

SEARCH_URL = BASE_URL + '/suche/%s?ext_search_submit=true&clip_page=%i&user_page=1&content_page=1&searchterm=%s&videos=1&v_atv_content=1&v_user_content=1&v_region=&m_region=&m_gender=&m_from_age='

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

##########################################################################################
@handler(PREFIX, TITLE, thumb = ICON, art = ART)
def MainMenu():
    oc = ObjectContainer()

    if Client.Platform == 'Android':
        oc.header  = 'Not supported'
        oc.message = 'This channel is not supported on Android clients'
        
        return oc

    title = "Suche"
    oc.add(
        InputDirectoryObject(
            key = Callback(Search),
            title = title, 
            prompt = title,
            thumb = R(ICON)
        )
    )
    
    pageElement = HTML.ElementFromURL(BASE_URL + '/mediathek')
    
    for item in pageElement.xpath("//*[@id='list_shows']//li"):
        url     = BASE_URL + item.xpath(".//a/@href")[0]
        title   = unicode(item.xpath(".//a/@title")[0].strip())
        thumb   = item.xpath(".//img/@src")[0]
        summary = ''.join(item.xpath(".//a/text()")).strip()
        
        oc.add(
            DirectoryObject(
                key =
                    Callback(
                        Videos,
                        url = url,
                        title = title,
                        thumb = thumb
                    ),
                title = title,
                thumb = thumb,
                summary = summary
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
@route(PREFIX + '/Videos', offset = int)
def Videos(url, title, thumb, offset = 0):
    oc = ObjectContainer(title2 = title)
    
    videos = GetVideoData(url = url, offset = offset, max_videos = VIDEOS_PER_PAGE)
    
    for video in videos:
        oc.add(
            EpisodeObject(
                url = video['link'],
                title = video['title'],
                show = video['show'],
                index = video['episode'],
                season = video['season'],
                summary = video['summary'],
                thumb = video['thumb'],
                duration = video['duration'],
                originally_available_at = video['date']
            )
        )
        
    if len(oc) > 0:
        if len(videos) >= VIDEOS_PER_PAGE:
            oc.add(
                NextPageObject(
                    key =
                        Callback(
                            Videos,
                            url = url,
                            title = title,
                            thumb = thumb,
                            offset = offset + len(videos)
                        )
                )
            )
    else:
        oc.header  = 'Sorry'
        oc.message = 'Could not find any content'
        
    return oc      


 