import React, { Component, Fragment } from 'react';
import EmptyTip from '../../components/empty-tip';
import Loading from '../../components/loading';
import { Button, ButtonGroup } from 'reactstrap';
import PinganShareLinkApproveInfoDialog from '../../components/dialog/pingan-share-link-approve-info-dialog';
import PinganFromUserDialog from '../../components/dialog/pingan-from-user-dialog';
import PinganLinkDownloadInfoDialog from '../../components/dialog/pingan-link-download-info-dialog';
import PinganShareLinkInfoDialog from '../../components/dialog/pingan-share-link-info-dialog.js';
import PinganShareLinkReceiverDialog from '../../components/dialog/pingan-share-link-receiver-dialog.js';
import { gettext, siteRoot, username, isDocs, isCompanySecurity, isSystemSecurity, pinganShareLinkBackupLibrary } from '../../utils/constants';
import { seafileAPI } from '../../utils/seafile-api';
import { Utils } from '../../utils/utils';
import URLDecorator from '../../utils/url-decorator';
import toaster from '../../components/toast';
import Notification from '../../components/common/notification';
import ZipDownloadDialog from '../../components/dialog/zip-download-dialog';
import Account from '../../components/common/account';
import ModalPortal from '../../components/modal-portal';
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";

class Content extends Component {

  constructor(props) {
    super(props);
  }

  render() {
    const { loading, errorMsg, items } = this.props;
    if (loading) {
      return <Loading />;
    } else if (errorMsg) {
      return <p className="error text-center">{errorMsg}</p>;
    } else {
      const emptyTip = (
        <EmptyTip>
          <h2>{gettext('没有外链审核信息')}</h2>
        </EmptyTip>
      );
      const table = (
        <Fragment>
          <table className="table-hover">
            <thead>
              <tr>
                <th width="3%">
                  <input type="checkbox" className="vam" onChange={this.props.onAllItemSelected} checked={this.props.isAllItemSelected}/>
                </th>
                <th width="27%">{'文件名字'}</th>
                <th width="15%">{'发送人'}</th>
                <th width="18%">{'接收人'}</th>
                <th width="17%">{'详细审批状态'}</th>
                <th width="20%">{'链接下载信息'}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => {
                return (<Item
                  key={index}
                  item={item}
                  onItemSelected={this.props.onItemSelected}
                />);
              })}
            </tbody>
          </table>
        </Fragment>
      );
      return items.length ? table : emptyTip;
    }
  }
}

class Item extends Component {

  constructor(props) {
    super(props);
    this.state = {
      isOpIconShown: false,
      isPinganApproveInfoDialogOpen: false,
      isPinganFromUserDialogOpen: false,
      isPinganLinkDownloadInfoDialogOpen: false,
      isPinganShareLinkInfoDialogOpen: false,
      isPinganShareLinkReceiverDialogOpen: false,
    };
  }

  handleMouseEnter = () => {
    this.setState({isOpIconShown: true});
  }

  handleMouseLeave = () => {
    this.setState({isOpIconShown: false});
  }

  togglePinganApproveInfoDialog = (e) => {
    this.setState({isPinganApproveInfoDialogOpen: !this.state.isPinganApproveInfoDialogOpen});
  }

  togglePinganFromUserDialog = (e) => {
    this.setState({isPinganFromUserDialogOpen: !this.state.isPinganFromUserDialogOpen});
  }

  togglePinganLinkDownloadInfoDialog = (e) => {
    this.setState({isPinganLinkDownloadInfoDialogOpen: !this.state.isPinganLinkDownloadInfoDialogOpen});
  }

  togglePinganShareLinkInfoDialog = (e) => {
    this.setState({isPinganShareLinkInfoDialogOpen: !this.state.isPinganShareLinkInfoDialogOpen});
  }

  togglePinganShareLinkReceiverDialog = (e) => {
    this.setState({isPinganShareLinkReceiverDialogOpen: !this.state.isPinganShareLinkReceiverDialogOpen});
  }

  onItemSelected = () => {
    this.props.onItemSelected(this.props.item);
  }

  render() {
    let { item } = this.props;
    let { isPinganApproveInfoDialogOpen, isPinganFromUserDialogOpen,
      isPinganLinkDownloadInfoDialogOpen, isPinganShareLinkInfoDialogOpen,
      isPinganShareLinkReceiverDialogOpen,} = this.state;
    return (
      <Fragment>
        <tr onMouseEnter={this.handleMouseEnter} onMouseLeave={this.handleMouseLeave}>
          <td>
            <input type="checkbox" className="vam" onChange={this.onItemSelected} checked={item.isSelected}/>
          </td>
          <td><a onClick={this.togglePinganShareLinkInfoDialog} href="#">{item.filename}</a></td>
          <td><a onClick={this.togglePinganFromUserDialog} href="#">{item.from_user}</a></td>
          <td><a onClick={this.togglePinganShareLinkReceiverDialog} href="#">{'查看接收人'}</a></td>
          <td><a onClick={this.togglePinganApproveInfoDialog} href="#">{'查看详细信息'}</a></td>
          <td><a onClick={this.togglePinganLinkDownloadInfoDialog} href="#">{'查看链接下载信息'}</a></td>
        </tr>
        {isPinganShareLinkInfoDialogOpen &&
          <PinganShareLinkInfoDialog
            toggle={this.togglePinganShareLinkInfoDialog}
            item={item}
          />
        }
        {isPinganFromUserDialogOpen &&
          <PinganFromUserDialog
            toggle={this.togglePinganFromUserDialog}
            item={item}
          />
        }
        {isPinganShareLinkReceiverDialogOpen &&
          <PinganShareLinkReceiverDialog
            toggle={this.togglePinganShareLinkReceiverDialog}
            item={item}
          />
        }
        {isPinganApproveInfoDialogOpen &&
          <PinganShareLinkApproveInfoDialog
            toggle={this.togglePinganApproveInfoDialog}
            shareLinkToken={item.share_link_token}
          />
        }
        {isPinganLinkDownloadInfoDialogOpen &&
          <PinganLinkDownloadInfoDialog
            toggle={this.togglePinganLinkDownloadInfoDialog}
            shareLinkToken={item.share_link_token}
          />
        }
      </Fragment>
    );
  }
}

class ApproveChainInfo extends Component {

  constructor(props) {
    super(props);
    this.state = {
      errorMsg: '',
      loading: true,
      pinganApproveStatusList: [],
      selectedItems: [],
      isAllItemSelected: false,
      isZipDialogOpen: false,
      startDate: null,
      endDate: null,
      fileNameForSearch: '',
      shareLinkCreator: '',
      backupRepoID: '',
    };
  }

  listPinganSecurityShareLinksReport = (start, end, searchFileName, searchShareLinkCreator) => {
    let url = seafileAPI.server;
    if (isCompanySecurity) {
      url += '/pingan-api/company-security/share-links-report/?';
    } else if (isSystemSecurity) {
      url += '/pingan-api/admin/share-links-report/?';
    }
    url += start ? 'start=' + start + '&' : '';
    url += end ? 'end=' + end + '&' : '';
    url += searchFileName ? 'filename=' + encodeURIComponent(searchFileName) + '&' : '';
    url += searchShareLinkCreator ? 'from_user=' + encodeURIComponent(searchShareLinkCreator) + '&' : '';
    return seafileAPI.req.get(url);
  }

  formatDate = (date) => {
    if (date === null)
      return date;
    let month = '' + (date.getMonth() + 1);
    let day = '' + date.getDate();
    let year = date.getFullYear();

    if (month.length < 2)
      month = '0' + month;
    if (day.length < 2)
      day = '0' + day;
    return [year, month, day].join('-');
  }

  componentDidMount() {
    this.showPinganApproveStatus();
  }

  showPinganApproveStatus = () => {
    let fromTimeStr = this.formatDate(this.state.startDate);
    let endTimeStr = this.formatDate(this.state.endDate);
    this.listPinganSecurityShareLinksReport(fromTimeStr, endTimeStr, this.state.fileNameForSearch, this.state.shareLinkCreator).then(res => {
      let pinganApproveStatusList = res.data.data.map(item => {
        item.isSelected = false;
        return item;
      });
      this.setState({
        pinganApproveStatusList: pinganApproveStatusList,
        backupRepoID: res.data.backup_repo_id,
        loading: false,
      });
    }).catch(error => {
      let errMessage = Utils.getErrorMsg(error);
      toaster.danger(errMessage);
    });
  }

  downloadShareLinksReport = () => {
    let fromTimeStr = this.formatDate(this.state.startDate);
    let endTimeStr = this.formatDate(this.state.endDate);
    let { fileNameForSearch, searchShareLinkCreator } = this.state;

    let url = seafileAPI.server;
    if (isCompanySecurity) {
      url += '/pingan-api/company-security/share-links-report/?';
    } else if (isSystemSecurity) {
      url += '/pingan-api/admin/share-links-report/?';
    }
    url += fromTimeStr ? 'start=' + fromTimeStr + '&' : '';
    url += endTimeStr ? 'end=' + endTimeStr + '&' : '';
    url += fileNameForSearch ? 'filename=' + encodeURIComponent(fileNameForSearch) + '&' : '';
    url += searchShareLinkCreator ? 'from_user=' + encodeURIComponent(searchShareLinkCreator) + '&' : '';

    location.href = url + 'excel=true';
  }

  downloadDownloadInfo = () => {
    let url = seafileAPI.server;
    if (isCompanySecurity) {
      url += '/pingan-api/company-security/share-link-download-info/?excel=true';
    } else if (isSystemSecurity) {
      url += '/pingan-api/admin/share-link-download-info/?excel=true';
    }
    this.state.pinganApproveStatusList.map(item => {
      url += '&share_link_token=' + item.share_link_token;
    });
    location.href = url;
  }

  handleStartDateChange = (date) => {
    this.setState({
      startDate: date
    });
  };

  handleEndDateChange = (date) => {
    this.setState({
      endDate: date
    });
  };

  saveFileNameForSearch = (e) => {
    this.setState({fileNameForSearch: e.target.value});
  }

  saveShareLinkCreator = (e) => {
    this.setState({shareLinkCreator: e.target.value});
  }

  onItemSelected = (curItem) => {
    let newPinganApproveStatusList = this.state.pinganApproveStatusList.map(item => {
      if (item.share_link_token == curItem.share_link_token) {
        item.isSelected = !item.isSelected;
        // update selecteItems
        if (item.isSelected) {
          let selectedItemsNew = this.state.selectedItems;
          selectedItemsNew.push(item);
          this.setState({selectedItems: selectedItemsNew});
        } else {
          let selectedItemsNew = this.state.selectedItems.filter(cur_item => {
            return item.share_link_token != cur_item.share_link_token;
          });
          this.setState({selectedItems: selectedItemsNew});
        }
      }
      return item;
    });
    this.setState({pinganApproveStatusList: newPinganApproveStatusList}, () => {
      // update isAllItemSelected
      if (this.state.selectedItems.length == this.state.pinganApproveStatusList.length) {
        this.setState({isAllItemSelected: true});
      } else {
        this.setState({isAllItemSelected: false});
      }
    });
  }

  onAllItemSelected = () => {
    if (this.state.isAllItemSelected) {
      this.setState({isAllItemSelected: false});
      let newPinganApproveStatusList = this.state.pinganApproveStatusList.map(item => {
        item.isSelected = false;
        return item;
      });
      this.setState({
        pinganApproveStatusList: newPinganApproveStatusList,
        selectedItems: [],
      });
    } else {
      this.setState({isAllItemSelected: true});
      let newPinganApproveStatusList = this.state.pinganApproveStatusList.map(item => {
        item.isSelected = true;
        return item;
      });
      this.setState({
        pinganApproveStatusList: newPinganApproveStatusList,
        selectedItems: newPinganApproveStatusList,
      });
    }
  }

  onItemsDownload = () => {
    if (this.state.selectedItems.length == 1) {
      let url = '';
      let path = '/';
      let direntPath = Utils.joinPath(path, this.state.selectedItems[0].source_obj_name);
      if (isSystemSecurity) {
          url = URLDecorator.getUrl({type: 'download_file_url', repoID: pinganShareLinkBackupLibrary, filePath: direntPath});
      } else {
          url = URLDecorator.getUrl({type: 'download_file_url', repoID: this.state.backupRepoID, filePath: direntPath});
      }
      location.href = url;
      return;
    } else if (this.state.selectedItems.length >= 2) {
      this.setState({
        isZipDialogOpen: true
      });
    }
  }

  closeZipDialog = () => {
    this.setState({
      isZipDialogOpen: false
    });
  }

  render() {
    let { errorMsg, loading } = this.state;
    return (
      <Fragment>
        <div className="main-panel-north">
          {this.state.selectedItems.length >= 1 &&
          <div className="d-flex">
            <ButtonGroup className="flex-row group-operations">
              <Button className="secondary group-op-item action-icon sf2-icon-download" title={gettext('Download')} onClick={this.onItemsDownload}></Button>
            </ButtonGroup>
          </div>
          }
          <div className="common-toolbar">
            <Notification />
            <Account />
          </div>
        </div>
        <div className="main-panel o-hidden">
          <div className="main-panel-north border-left-show" style={{'zIndex':'10'}}>
            <div className="">
              {'从'}
              <DatePicker
                className="mr-2"
                dateFormat="yyyy/MM/dd"
                selected={this.state.startDate}
                onChange={this.handleStartDateChange}
                placeholderText="选择日期"
              />
              {'到'}
              <DatePicker
                className="mr-2"
                dateFormat="yyyy/MM/dd"
                selected={this.state.endDate}
                onChange={this.handleEndDateChange}
                placeholderText="选择日期"
              />
              <input onChange={this.saveFileNameForSearch} className="mr-2" style={{width:'100px'}} placeholder="按文件名搜索"></input>
              <input onChange={this.saveShareLinkCreator} className="mr-2" style={{width:'100px'}} placeholder="按创建者搜索"></input>
            </div>
            <button className="btn btn-secondary operation-item ml-2 mr-2" title={gettext('Export Excel')} onClick={this.showPinganApproveStatus}>
              {gettext('查看审批')}
            </button>
            <button className="btn btn-secondary operation-item ml-2 mr-2" title={gettext('Export Excel')} onClick={this.downloadShareLinksReport}>
              {gettext('下载审批信息')}
            </button>
            <button className="btn btn-secondary operation-item ml-2 mr-2" title={gettext('Export Excel')} onClick={this.downloadDownloadInfo}>
              {gettext('下载链接下载信息')}
            </button>
          </div>
          <div className="main-panel-center flex-row">
            <div className="cur-view-container">
              <div className="cur-view-content">
                <Content
                  loading={loading}
                  errorMsg={errorMsg}
                  items={this.state.pinganApproveStatusList}
                  onItemSelected={this.onItemSelected}
                  onAllItemSelected={this.onAllItemSelected}
                  isAllItemSelected={this.state.isAllItemSelected}
                />
              </div>
            </div>
          </div>
        </div>
        {this.state.isZipDialogOpen &&
        <ModalPortal>
          <ZipDownloadDialog
            repoID={this.state.backupRepoID}
            path='/'
            target={this.state.selectedItems.map(item => item.source_obj_name)}
            toggleDialog={this.closeZipDialog}
          />
        </ModalPortal>
        }
      </Fragment>
    );
  }
}

export default ApproveChainInfo;
