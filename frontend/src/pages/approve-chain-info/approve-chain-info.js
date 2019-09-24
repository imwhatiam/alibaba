import React, { Component, Fragment } from 'react';
import { gettext } from '../../utils/constants';
import EmptyTip from '../../components/empty-tip';
import Loading from '../../components/loading';
import PinganApproveStatusDialog from '../../components/dialog/pingan-approve-status-dialog';
import PinganFromUserDialog from '../../components/dialog/pingan-from-user-dialog';
import PinganLinkDownloadInfoDialog from '../../components/dialog/pingan-link-download-info-dialog';

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
                <th width="10%">{'文件名字'}</th>
                <th width="12%">{'接收对象'}</th>
                <th width="8%">{'创建时间'}</th>
                <th width="8%">{'链接过期时间'}</th>
                <th width="14%">{'下载链接'}</th>
                <th width="9%">{'DLP审批状态'}</th>
                <th width="9%">{'DLP审批时间'}</th>
                <th width="9%">{'审核状态'}</th>
                <th width="8%">{'发送人信息'}</th>
                <th width="13%">{'链接下载信息'}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => {
                return (<Item
                  key={index}
                  item={item}
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
      isPinganApproveStatusDialogOpen: false,
      isPinganFromUserDialogOpen: false,
      isPinganLinkDownloadInfoDialogOpen: false,
    };
  }

  handleMouseEnter = () => {
    this.setState({isOpIconShown: true});
  }

  handleMouseLeave = () => {
    this.setState({isOpIconShown: false});
  }

  togglePinganApproveStatusDialog = (e) => {
    this.setState({isPinganApproveStatusDialogOpen: !this.state.isPinganApproveStatusDialogOpen});
  }

  togglePinganFromUserDialog = (e) => {
    this.setState({isPinganFromUserDialogOpen: !this.state.isPinganFromUserDialogOpen});
  }

  togglePinganLinkDownloadInfoDialog = (e) => {
    this.setState({isPinganLinkDownloadInfoDialogOpen: !this.state.isPinganLinkDownloadInfoDialogOpen});
  }

  render() {
    let { item } = this.props;
    let { isOpIconShown, isPinganApproveStatusDialogOpen, isPinganFromUserDialogOpen,
      isPinganLinkDownloadInfoDialogOpen } = this.state;

    let iconVisibility = isOpIconShown ? '' : ' invisible'; 
    let deleteIconClassName = 'op-icon sf2-icon-delete' + iconVisibility;
    return (
      <Fragment>
        <tr onMouseEnter={this.handleMouseEnter} onMouseLeave={this.handleMouseLeave}>
          <td><a href={item.share_link_url}>{item.filename}</a></td>
          <td>{item.send_to}</td>
          <td>{item.created_at}</td>
          <td>{item.expiration}</td>
          <td>{item.share_link_url}</td>
          <td>{item.dlp_status}</td>
          <td>{item.dlp_vtime}</td>
          <td><a onClick={this.togglePinganApproveStatusDialog} href="#">{'查看审核信息'}</a></td>
          <td><a onClick={this.togglePinganFromUserDialog} href="#">{'查看发送人'}</a></td>
          <td><a onClick={this.togglePinganLinkDownloadInfoDialog} href="#">{'查看链接下载信息'}</a></td>
        </tr>
        {isPinganApproveStatusDialogOpen &&
          <PinganApproveStatusDialog 
            toggle={this.togglePinganApproveStatusDialog}
            item={item}
          />
        }
        {isPinganFromUserDialogOpen &&
          <PinganFromUserDialog
            toggle={this.togglePinganFromUserDialog}
            item={item}
          />
        }
        {isPinganLinkDownloadInfoDialogOpen &&
          <PinganLinkDownloadInfoDialog
            toggle={this.togglePinganLinkDownloadInfoDialog}
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
      loading: false,
    };
  }

  render() {
    let { errorMsg, loading } = this.state;
    return (
      <Fragment>
        <div className="main-panel-center flex-row">
          <div className="cur-view-container">
            <div className="cur-view-content">
              <Content
                loading={loading}
                errorMsg={errorMsg}
                items={this.props.pinganApproveStatusList}
              />
            </div>
          </div>
        </div>
      </Fragment>
    );
  }
}

export default ApproveChainInfo;
