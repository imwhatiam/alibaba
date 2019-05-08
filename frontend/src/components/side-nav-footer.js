import React, { Fragment } from 'react';
import { gettext, mediaUrl, siteRoot, sideNavFooterCustomHtml, extraAppBottomLinks, additionalAppBottomLinks } from '../utils/constants';
import { gettext, mediaUrl, siteRoot, sideNavFooterCustomHtml, extraAppBottomLinks } from '../utils/constants';
import ModalPortal from './modal-portal';
import AboutDialog from './dialog/about-dialog';

class SideNavFooter extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      isAboutDialogShow: false,
    };
  }

  onAboutDialogToggle = () => {
    this.setState({isAboutDialogShow: !this.state.isAboutDialogShow});
  }

  renderExternalAppLinks = () => {
    if (additionalAppBottomLinks && (typeof additionalAppBottomLinks) === 'object') {
      let keys = Object.keys(additionalAppBottomLinks);
      return keys.map((key, index) => {
        return <a key={index} className="item" href={additionalAppBottomLinks[key]}>{key}</a>;
      });
    }
    return null;
  }

  render() {
    if (sideNavFooterCustomHtml) {
      return (<div className='side-nav-footer' dangerouslySetInnerHTML={{__html: sideNavFooterCustomHtml}}></div>);
    }
    return (
      if (window.app.config.lang === 'zh-cn') {
        return (
          <div className="side-nav-footer">
            <div rel="noopener noreferrer" className="item">
              <img src={mediaUrl + 'img/alibaba-information-platfrom.png'}  height="22" style={{marginRight: 'auto',}} />
            </div>
            <a href={siteRoot + 'help/'} target="_blank" rel="noopener noreferrer" className="item last-item" style={{marginLeft: 'auto',}}>{'帮助'}</a>
          </div>
        );
      } else {
        return (
          <div className="side-nav-footer">
            <div rel="noopener noreferrer" className="item">
              <img src={mediaUrl + 'img/alibaba-information-platfrom.png'}  height="22" style={{marginRight: 'auto',}} />
            </div>
            <a href={siteRoot + 'help/'} target="_blank" rel="noopener noreferrer" className="item last-item" style={{marginLeft: 'auto',}}>{'Help'}</a>
          </div>
        );
      }
    );
  }
}

export default SideNavFooter;
