"""Tests for capsteps_ingest.extract, using short markup excerpts modeled on real captures.

Each fixture is a trimmed excerpt of the archived capsteps.com homepage (capture
timestamp noted), reduced to the structure the extractor relies on.

References:
    [PYTEST-DOCS] https://docs.pytest.org/en/stable/
    [WAYBACK-CAPSTEPS-HOME] https://web.archive.org/web/2006*/capsteps.com/
"""

from capsteps_ingest.extract import extract_copyright, extract_sightings, fix_drop_cap, linearize

BASE = "http://www.capsteps.com:80/"

# 19970120075125: bold title BEFORE the format links; original in [<i>...</i>].
HTML_1997 = """<hr> <b> I </b>srael gives control of most of Hebron over to Palestinians.
<b>I'm In Hebron</b> [<i>Dancing Cheek To Cheek</i>]
[<a href="/sounds/hebron.au"> Sun/AU format </a> | <a href="/sounds/hebron.ram"> RealAudio/RA format </a> ] <hr>"""

# 20010202083100: "MP3 format" link, then bold title, then <i>[ original ]</i>, then album.
HTML_2001 = """<hr><i> Week of January 22 </i> <b> B YE, BYE BILL! </b> Clinton clears out for Dubya.
<a href="/sounds/zipper.au"><img src="x.gif"></a> <a href="/sounds/zipper.mp3"> MP3 format </a>
<b> Old Man Zipper </b> <i> [ Old Man River ] </i>
<a href="/sounds/zipper.ra"> [Download </a> | <a href="/sounds/zipper.ram"> Streaming] </a>
From the album <a href="/albums/"> Unzippin' My Doo-Dah </a> <hr>"""

# 20130113015325: <h3> heading, title in link (inside <strong>), album with year.
HTML_2013 = """<hr><h3> Robert Bork (1927-2012) </h3> Once upon a time, nominees said what they thought.
<a href="/sounds/bork-supremes.mp3"> <strong>The Supremes</strong></a>
From the album <a href="/albums/"><em>Workin' 9 to 10</em></a> (1987). <hr>"""

# 20210110030526: title in link, original in brackets with an empty iTunes link, album in <em>.
HTML_2021 = """<hr><em> We put the MOCK in Democracy! </em> Week of January 4 B rexit is finally here.
<a href="/sounds/brexit-woes.mp3"> The Many Woes of Brexit</a>
[ The Yellow Rose of Texas <a href="https://geo.music.apple.com/x"> </a> ]
From the album <em><a href="/albums/"> The Lyin' Kings </a> (2019)</em>.
<hr> Week of December 28 C ongress tucked plenty of extra spending into the bill.
<a href="/sounds/xmas-spendingspree.mp3"> Oh, Spending Spree </a> [ Oh, Christmas Tree ] <hr>
<p>Copyright &copy; 2021 Capitol Steps. All rights reserved.</p>"""


def only(html):
    """Extract sightings and index by slug. References: None."""
    return {s.slug: s for s in extract_sightings(html, BASE)}


def test_1997_bold_title_before_links():
    """References: [WAYBACK-CAPSTEPS-HOME] capture 19970120075125."""
    s = only(HTML_1997)["hebron"]
    assert (s.title, s.title_from, s.original_song) == ("I'm In Hebron", "bold", "Dancing Cheek To Cheek")
    assert "Hebron over to Palestinians" in s.description and "I'm In Hebron" not in s.description


def test_2001_bold_title_inside_link_group_skips_dropcap_heading():
    """References: [WAYBACK-CAPSTEPS-HOME] capture 20010202083100."""
    s = only(HTML_2001)["zipper"]
    assert (s.title, s.title_from) == ("Old Man Zipper", "bold")
    assert s.original_song == "Old Man River"
    assert s.album == "Unzippin' My Doo-Dah" and s.week == "January 22"


def test_2013_link_title_and_album_year():
    """References: [WAYBACK-CAPSTEPS-HOME] capture 20130113015325."""
    s = only(HTML_2013)["bork-supremes"]
    assert (s.title, s.title_from) == ("The Supremes", "link")
    assert (s.album, s.album_year) == ("Workin' 9 to 10", "1987")
    assert s.description.startswith("Robert Bork (1927-2012) Once upon a time")


def test_2021_two_songs_tagline_and_dropcaps():
    """References: [WAYBACK-CAPSTEPS-HOME] capture 20210110030526."""
    songs = only(HTML_2021)
    brexit, spree = songs["brexit-woes"], songs["xmas-spendingspree"]
    assert (brexit.title, brexit.original_song) == ("The Many Woes of Brexit", "The Yellow Rose of Texas")
    assert (brexit.album, brexit.album_year) == ("The Lyin' Kings", "2019")
    assert brexit.description == "Brexit is finally here."
    assert (spree.title, spree.original_song, spree.week) == ("Oh, Spending Spree", "Oh, Christmas Tree", "December 28")
    assert spree.description.startswith("Congress tucked")


def test_extract_copyright():
    """References: None."""
    html = ("Site by Moose Hill Bitworks. Recordings and lyrics Copyright &copy; by Newport and Eaton. "
            "(Recordings and lyrics prior to 2007 Copyright &amp;copy; by Strauss, Newport &amp; Eaton or by "
            "Strauss &amp; Newport. This work includes parodies of the original songs. All rights reserved, "
            "including the right of reproduction. These audio files are provided for individual listening only. "
            "Do not redistribute. Surgeon General's Warning: ... call us at (703) 555-0100.")
    assert extract_copyright(html) == (
        "Recordings and lyrics Copyright © by Newport and Eaton. (Recordings and lyrics prior to 2007 "
        "Copyright © by Strauss, Newport & Eaton or by Strauss & Newport.) This work includes parodies of the "
        "original songs. All rights reserved, including the right of reproduction. These audio files are "
        "provided for individual listening only. Do not redistribute.")


def test_linearize_marks_audio_and_bold():
    """References: [PY-HTML-PARSER]."""
    out = linearize('<b>Hi <a href="/sounds/x.mp3">MP3 format</a> there</b><script>var a="/sounds/y.mp3"</script>', BASE)
    assert "⟦A:x|mp3|MP3 format⟧" in out and "y.mp3" not in out


def test_fix_drop_cap():
    """References: None."""
    assert fix_drop_cap("W ho was naughty. T he end. I am. A dog.") == "Who was naughty. The end. I am. A dog."
    assert fix_drop_cap("A town in New Hampshire") == "A town in New Hampshire"
    assert fix_drop_cap("A l Gore gets his turn.") == "Al Gore gets his turn."  # capture 20000814
    assert fix_drop_cap("I t is over.") == "It is over."
    assert fix_drop_cap("I am here.") == "I am here."


def test_titles_containing_here_are_not_generic():
    """Regression: "here" inside a real title (captures 2007, 2012). References: None."""
    html = ('<hr>Democrats return. <a href="/sounds/waffling.mp3"> MP3 format </a> <b> Here We Come a-Waffling </b>'
            ' [ Here We Come a Wassailing ] <a href="/sounds/waffling.ram">Streaming]</a> <hr>'
            '<a href="/sounds/cain-grandma.mp3">Grandma Got the Creeps Cuz Herman Cain\'s Here</a>'
            ' [ Grandma Got Run Over By a Reindeer ] Get the album: Weiner Wonderland (2011) — only $3.99 <hr>')
    songs = only(html)
    assert songs["waffling"].title == "Here We Come a-Waffling"
    assert songs["cain-grandma"].title == "Grandma Got the Creeps Cuz Herman Cain's Here"
    assert (songs["cain-grandma"].album, songs["cain-grandma"].album_year) == ("Weiner Wonderland", "2011")


def test_lowercase_link_text_is_prose_not_title():
    """Regression: capture 20020826072544 linked prose text. References: None."""
    html = ('<hr>Updated from the <a href="/sounds/saltlakecity.mp3">pre-Games bribery parody</a>: '
            '<b>The Boy From Salt Lake City</b> [ The Boy From New York City ] <hr>')
    assert only(html)["saltlakecity"].title == "The Boy From Salt Lake City"


def test_lowercase_bold_and_run_on_links_are_not_titles():
    """Regression: captures 20070325202243 (bold "podcast"), 20170711104555 ("Donald Trump
    previewed the show"), 20001017101615 ("Jim Lehrer of PBS will"). References: None."""
    html = ('<hr><b>Coming Soon:</b> Download this <a href="/sounds/radio-0704-promo.mp3">promo clip</a>'
            ' or get it via <a href="/podcast/"><b>podcast</b></a>. <hr>'
            '<b>Fireworks Galore!</b> Download our <a href="/radio/"><b>Fourth of July Radio Special</b></a>!'
            ' <a href="/sounds/radio-1707-promo60.mp3">Donald Trump previewed</a> the show in this'
            ' <a href="/sounds/radio-1707-promo60.mp3">promo clip</a>! <hr>'
            'Jim Lehrer of <a href="/sounds/bigbird.ram">PBS</a> will moderate. <hr>')
    songs = only(html)
    assert songs["radio-0704-promo"].title == "Coming Soon"
    assert songs["radio-1707-promo60"].title == "Fourth of July Radio Special"
    assert songs["bigbird"].title == ""


def test_combined_format_labels_and_format_suffix():
    """Regression: "RA Streaming" link (20101023011853) and "Pack the Knife (MP3)" (20060810061657).
    References: None."""
    html = ('<hr>Spending. <a href="/sounds/subprime2.mp3">MP3</a> <a href="/sounds/subprime2.ram">RA Streaming</a>'
            ' <b>Subprime Mortgage Holders</b> <hr>'
            'Bombs away: <a href="/sounds/packtheknife.mp3">Pack the Knife (MP3)</a> <hr>')
    songs = only(html)
    assert songs["subprime2"].title == "Subprime Mortgage Holders"
    assert songs["packtheknife"].title == "Pack the Knife"


def test_site_navigation_and_page_title_are_skipped():
    """Regression: 2014-2017 descriptions began "The Capitol Steps - Site navigation: Home ..."
    (capture 20160113031912). References: None."""
    html = ('<html><head><title>The Capitol Steps - We put the MOCK in Democracy</title></head><body>'
            '<div id="navigation"><h5>Site navigation:</h5><ul><li><a href="/">Home</a></li>'
            '<li><a href="/albums/">Albums</a><br/></li></ul></div>'
            '<div id="main">Week of July 10 <b>Big News</b> Congress did a thing.'
            ' <a href="/sounds/thing.mp3">The Thing</a> [ Old Song ] <hr></div></body></html>')
    song = only(html)["thing"]
    assert (song.title, song.week, song.original_song) == ("The Thing", "July 10", "Old Song")
    assert song.description == "Big News Congress did a thing."


def test_link_title_followed_by_and_is_a_list_item_not_prose():
    """Regression: captures 20020721222416 and 20070104010002 (album page). References: None."""
    html = ('<hr><b>Andersen Convicted!</b> Hear the saga of <a href="/sounds/enron.ram">Enron - ron</a>'
            ' and other great hits on our latest album. <hr>'
            'Rudolph the Two-Faced Reindeer <a href="/sounds/doyoufear.mp3">Do You Fear What I Fear?</a>'
            ' and many more. <hr>')
    songs = only(html)
    assert songs["enron"].title == "Enron - ron"
    assert songs["doyoufear"].title == "Do You Fear What I Fear?"


def test_clean_album():
    """Regression: album debris seen in captures 2002-2012. References: None."""
    from capsteps_ingest.extract import clean_album
    assert clean_album("! Desperate Housemembers") == ("Desperate Housemembers", "")
    assert clean_album("76 Bad Loans.)") == ("76 Bad Loans", "")
    assert clean_album("Georgie on My Mind .)") == ("Georgie on My Mind", "")
    assert clean_album("Liberal Shop of Horrors (Songs of 2010)") == ("Liberal Shop of Horrors", "2010")
    assert clean_album("I Want It Dad's Way (Special Release 2005)") == ("I Want It Dad's Way (Special Release 2005)", "")


def test_site_prompts_in_brackets_are_not_original_songs():
    """Regression: Lirty Dies pages (e.g. lirty-1012) bracketed a read/download prompt. References: None."""
    html = ('<hr>Rirty Dotten Lumors. <a href="/sounds/lirty-1012.mp3">Lirty Dies: Midterm Medley</a>'
            ' [ You can read and download more Lirty Dies ] <hr>'
            '<a href="/sounds/medley.mp3">GOP Medley</a> [ If I Only Had a Brain , Macho Man ] <hr>')
    songs = only(html)
    assert songs["lirty-1012"].original_song == ""
    assert songs["medley"].original_song == "If I Only Had a Brain, Macho Man"


def test_inline_song_link_is_prose_and_does_not_cut_next_blurb():
    """Regression: capture 20191015204704 linked an earlier song inline ("such as the
    Wedtech scandal, ...") before the featured song. References: None."""
    html = ('<hr>Week of October 14 Trump honored Edwin Meese, but skipped events such as the '
            '<a href="/sounds/meese-pieces.mp3">Wedtech scandal</a>, the Iran-Contra scandal, and the Meese report. '
            '<a href="/sounds/meeseketeers.mp3">The Meeseketeers</a> [ Mickey Mouse Club Alma Mater ] <hr>')
    songs = only(html)
    assert songs["meese-pieces"].title == ""
    assert songs["meeseketeers"].title == "The Meeseketeers"
    assert songs["meeseketeers"].description == ("Trump honored Edwin Meese, but skipped events such as the "
                                                 "Wedtech scandal, the Iran-Contra scandal, and the Meese report.")


def test_blurb_starts_at_caps_lead_and_special_album_phrasing():
    """Regression: captures 20021030004940 (unrelated note before the blurb) and
    20070206020255 ("From the special holiday album ..."). References: None."""
    html = ('<hr>Week of October 28 Cheney sings live on Madblast.com! <b>FOLLOWING THE DEATH</b> of Paul Wellstone, '
            'Democrats tap Mondale. <a href="/sounds/mondale-wreck.mp3">MP3 format</a>'
            ' <b>The Wreck of the Walter Fritz Mondale</b> [ The Wreck of the Edmund Fitzgerald ] <hr>'
            '<b>ON A TRIP</b> to Wall Street, Bush speaks. <a href="/sounds/frosty-ceo.mp3">MP3 format</a>'
            ' <b>Frosty, The Chairman</b> [ Frosty, The Snowman ] From the special holiday album O Christmas Bush. <hr>'
            'Spitzer is back. <a href="/sounds/lirty-ny.mp3">Lirty Dies: Yoo Nork</a> [ Read these Lirty Dies ] <hr>')
    songs = only(html)
    assert songs["mondale-wreck"].description == "FOLLOWING THE DEATH of Paul Wellstone, Democrats tap Mondale."
    assert songs["frosty-ceo"].album == "O Christmas Bush"
    assert songs["lirty-ny"].original_song == ""
