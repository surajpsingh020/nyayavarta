import pytest
from scripts.ingest.process_aws_sc import parse_html_metadata

def test_parse_html_metadata():
    html = """
    <font size='4'> <strong>VIJAY SINGH @ VIJAY KR. SHARMA<span class='fst-italic'> versus </span>THE STATE OF BIHAR </strong>- <span class='escrText'>[2024] 10 S.C.R. 108</span><span class='ncDisplay'>2024 INSC 735</span><input type='hidden' id='cnr' value=ESCR010004822024></button></font><br><strong>Coram : BELA M. TRIVEDI<sup style="color: #268e97;font-size: 22px;top: 0;" class="tooltip-sup" data-tooltip="Author">*</sup>, SATISH CHANDRA SHARMA</strong><br> Issue for Consideration Issue arose as regards sustainablility of the findings of the High Court holding the appellants guilty of commission of offences u/ss. 302/34 and 364/34 IPC; as also the approach of the High Court, if in line with the settled law for reversing an acquittal &ndash; ss. 302/34 and 364/34 &ndash; Kidnapping or abducting in order to murder &ndash; Abduction and murder of woman over a property dispute &ndash; Factum of her death discovered in furtherance of written report lodged by informant and brother- in-law of the victim &ndash; Conviction and<br><strong class='caseDetailsTD' ><span style='color:#212F3D' > Decision Date :</span><font color='green'> 25-09-2024</font><span style='color:#212F3D' > | Case No :</span><font color='green'> CRIMINAL APPEAL No. 1031/2015</font><span style='color:#212F3D' > | Disposal Nature :</span><font color='green'> Disposed off</font>   <span style='color:#212F3D' > |  Bench :</span><font color='green'> 2 Judges</font></strong>
    """
    
    meta = parse_html_metadata(html)
    assert meta["title"].startswith("VIJAY SINGH")
    assert "BELA M. TRIVEDI" in meta["judges"]
    assert meta["decision_date"] == "25-09-2024"
    assert "1031/2015" in meta["case_no"]
    assert meta["disposal_nature"] == "Disposed off"
    assert meta["bench"] == "2 Judges"
